#!/usr/bin/env python3
"""Snapshot the live Mode A runtime into pins/<harness/VERSION>/.

Usage:
    python scripts/publish_harness_release.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.harness_pin.pin import PinError, publish  # noqa: E402


def main() -> int:
    try:
        dest = publish()
    except PinError as e:
        print(f"publish failed: {e}", file=sys.stderr)
        return 2
    print(f"Published pin: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
