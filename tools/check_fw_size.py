#!/usr/bin/env python3
"""Usage: check_fw_size.py <firmware.bin> <limit-file>. Exit 1 if the bin exceeds the limit."""
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    size = Path(argv[1]).stat().st_size
    limit = int(Path(argv[2]).read_text().strip())
    print(f"firmware size: {size} bytes, limit: {limit} bytes")
    if size > limit:
        print(f"FAIL: {size - limit} bytes over the limit")
        return 1
    print(f"OK: {limit - size} bytes headroom")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
