"""PlatformIO pre-script: minify + gzip firmware/web/app.{css,js} into web_assets.h.

The header goes to $BUILD_DIR/generated/ (added to CPPPATH) and is rewritten only when its
content changes, so unchanged assets do not trigger a rebuild.
"""
import sys
from pathlib import Path

Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

project = Path(env["PROJECT_DIR"])  # noqa: F821
sys.path.insert(0, str(project.parent / "tools"))
import webasset  # noqa: E402

web = project / "web"
assets = {
    "app_css": webasset.gzip_bytes(
        webasset.minify_css((web / "app.css").read_text(encoding="utf-8")).encode()
    ),
    "app_js": webasset.gzip_bytes(
        webasset.minify_js((web / "app.js").read_text(encoding="utf-8")).encode()
    ),
}
out_dir = Path(env.subst("$BUILD_DIR")) / "generated"  # noqa: F821
out_dir.mkdir(parents=True, exist_ok=True)
header = out_dir / "web_assets.h"
text = webasset.render_header(assets)
if not header.exists() or header.read_text(encoding="utf-8") != text:
    header.write_text(text, encoding="utf-8")
print(f"embed_web: app.css {len(assets['app_css'])} B gz, app.js {len(assets['app_js'])} B gz")
env.Append(CPPPATH=[str(out_dir)])  # noqa: F821
