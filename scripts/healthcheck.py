#!/usr/bin/env python3
"""Probe the containerized API without adding curl to the runtime image."""

from __future__ import annotations

import json
import sys
import urllib.request


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "18080"
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - CLI probe must report any failure
        print(f"health probe failed: {exc}", file=sys.stderr)
        return 1
    if payload.get("status") != "ok":
        print(f"unexpected health payload: {payload}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
