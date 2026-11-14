"""PlatformIO pre-script: inject the repo-root VERSION as -DGB_VERSION."""
from pathlib import Path

Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

version_file = Path(env["PROJECT_DIR"]).parent / "VERSION"  # noqa: F821
version = version_file.read_text(encoding="utf-8").strip()
# Escape so the compiler sees a C string literal: "0.1.0"
env.Append(CPPDEFINES=[("GB_VERSION", env.StringifyMacro(version))])  # noqa: F821
