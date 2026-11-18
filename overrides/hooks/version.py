"""MkDocs hook: expose the repo VERSION as config.extra.version (shown in the footer)."""

from pathlib import Path


def on_config(config):
    version_file = Path(config["config_file_path"]).parent / "VERSION"
    config["extra"]["version"] = version_file.read_text(encoding="utf-8").strip()
    return config
