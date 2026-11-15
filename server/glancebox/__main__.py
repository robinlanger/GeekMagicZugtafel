"""Command line: ``python -m glancebox serve|render``."""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import os
import sys
import time
from pathlib import Path

from .config import ConfigError, load_config
from .pages import load_page_types, validate_config
from .render import RenderError

DEFAULT_CONFIG = "/config/config.yaml"


def _load(path: str):
    cfg = load_config(Path(path))
    types = load_page_types(cfg.pages_dirs)
    return validate_config(cfg, types), types


def _serve(args) -> int:
    import uvicorn

    from .app import create_app
    from .frames import FrameStore

    cfg, types = _load(args.config)
    app = create_app(cfg, FrameStore(len(cfg.pages)), types=types)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


async def _render(cfg, types, index: int) -> bytes:
    from .frames import render_page
    from .push import PushInbox
    from .render import Renderer

    page = cfg.pages[index]
    async with Renderer() as renderer:
        return await render_page(page, types[page.type], cfg, renderer, time.time(),
                                 PushInbox())


def _render_cmd(args) -> int:
    cfg, types = _load(args.config)
    if not 0 <= args.index < len(cfg.pages):
        raise ConfigError(f"page index {args.index} out of range (0..{len(cfg.pages) - 1})")
    jpeg = asyncio.run(_render(cfg, types, args.index))
    out = Path(args.output)
    if out.suffix.lower() == ".png":
        from PIL import Image

        buf = io.BytesIO()
        Image.open(io.BytesIO(jpeg)).convert("RGB").save(buf, "PNG")
        out.write_bytes(buf.getvalue())
    else:
        out.write_bytes(jpeg)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="glancebox")
    default_cfg = os.environ.get("GLANCEBOX_CONFIG", DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the HTTP server")
    serve.add_argument("--config", default=default_cfg)
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(func=_serve)
    render = sub.add_parser("render", help="render one page once")
    render.add_argument("index", type=int)
    render.add_argument("-o", "--output", required=True)
    render.add_argument("--config", default=default_cfg)
    render.set_defaults(func=_render_cmd)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        return args.func(args)
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 2
    except RenderError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
