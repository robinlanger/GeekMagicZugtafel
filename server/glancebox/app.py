"""HTTP API polled by the device, plus the preview UI."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from collections.abc import Callable

import jinja2
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from . import __version__
from .config import AppConfig
from .frames import TEMPLATES_DIR, Frame, FrameStore, run_worker
from .pages import PageType, load_page_types
from .render import Renderer
from .schedule import clamp_next_in, select

log = logging.getLogger(__name__)

ERROR_NEXT_IN = 10
_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def _etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    for part in header.split(","):
        part = part.strip()
        part = part.removeprefix("W/")
        if part.strip('"') == etag:
            return True
    return False


def on_worker_done(task: asyncio.Task, exit_process: Callable[[int], object] = os._exit) -> None:
    """Done callback of the render worker: a dead worker means no page is ever refreshed
    again, so log why and exit non-zero; the container restart policy brings us back.
    Cancellation is the normal shutdown path and is ignored."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        log.critical("render worker died, exiting", exc_info=exc)
    else:
        log.critical("render worker died (returned), exiting")
    exit_process(1)


def create_app(cfg: AppConfig, store: FrameStore, clock: Callable[[], float] = time.time, *,
               types: dict[str, PageType] | None = None, start_worker: bool = True) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        if not start_worker:
            yield
            return
        page_types = types if types is not None else load_page_types(cfg.pages_dirs)
        async with Renderer() as renderer:
            await store.build_error_frame(renderer)
            task = asyncio.create_task(run_worker(cfg, page_types, renderer, store))
            task.add_done_callback(on_worker_done)
            app.state.renderer, app.state.worker_task = renderer, task
            try:
                yield
            finally:
                task.remove_done_callback(on_worker_done)
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.renderer = app.state.worker_task = None  # set by lifespan when the worker runs
    durations = [p.duration for p in cfg.pages]

    def jpeg_response(request: Request, frame: Frame, next_in: int) -> Response:
        headers = {"ETag": f'"{frame.etag}"', "X-Next-In": str(next_in),
                   "Cache-Control": "no-store"}
        if _etag_matches(request.headers.get("if-none-match"), frame.etag):
            return Response(status_code=304, headers=headers)
        return Response(frame.jpeg, media_type="image/jpeg", headers=headers)

    @app.get("/api/v1/frame")
    def frame(request: Request, id: str = "", fw: str = "") -> Response:
        log.debug("frame request id=%s fw=%s", id, fw)
        now = clock()
        index, to_switch = select(durations, store.available(now), now)
        if index is None:
            return jpeg_response(request, store.error_frame, ERROR_NEXT_IN)
        current = store.get(index, now)
        if current is None:  # went stale between the two calls
            return jpeg_response(request, store.error_frame, ERROR_NEXT_IN)
        last = store.last_attempt(index)
        until_refresh = 0.0 if last is None else max(
            0.0, last + cfg.pages[index].refresh - now)
        return jpeg_response(request, current, clamp_next_in(min(to_switch, until_refresh)))

    @app.get("/preview/{index}.jpg")
    def preview(index: int) -> Response:
        current = store.get(index, clock())
        if current is None:
            raise HTTPException(404, "not rendered yet")
        return Response(current.jpeg, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        now = clock()
        rows = []
        for p in cfg.pages:
            current = store.get(p.index, now)
            rows.append({
                "index": p.index, "type": p.type, "error": store.last_error(p.index),
                "age": None if current is None else int(now - current.rendered_at),
                "has_frame": current is not None,
            })
        return _env.get_template("index.html").render(pages=rows, version=__version__)

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        task, renderer = app.state.worker_task, app.state.renderer
        worker_ok = task is None or not task.done()
        browser_ok = renderer is None or renderer.healthy()
        body = {"version": __version__, "pages_ok": sum(store.available(clock())),
                "worker_ok": worker_ok, "browser_ok": browser_ok}
        return JSONResponse(body, status_code=200 if worker_ok and browser_ok else 503)

    return app
