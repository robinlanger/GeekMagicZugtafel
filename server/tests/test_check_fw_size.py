import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "check_fw_size.py"


def run(tmp_path: Path, size: int, limit: str):
    binf = tmp_path / "fw.bin"
    binf.write_bytes(b"\0" * size)
    lim = tmp_path / "limit.txt"
    lim.write_text(limit)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(binf), str(lim)], check=False, capture_output=True, text=True
    )


def test_within_limit(tmp_path):
    r = run(tmp_path, 1000, "2000\n")
    assert r.returncode == 0
    assert "1000" in r.stdout and "2000" in r.stdout


def test_exactly_at_limit(tmp_path):
    assert run(tmp_path, 2000, "2000").returncode == 0


def test_over_limit(tmp_path):
    r = run(tmp_path, 2001, "2000")
    assert r.returncode == 1
    assert "2001" in r.stdout and "2000" in r.stdout
