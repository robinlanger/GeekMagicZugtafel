"""HTTP API polled by the device, plus the preview UI."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable

import jinja2
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

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
            try:
                yield
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
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
    def healthz() -> dict:
        return {"version": __version__, "pages_ok": sum(store.available(clock()))}

    return app
