"""Tiny structured-metrics emitter (1.5).

Writes one JSON line per event to stdout. In ECS this is picked up by the CloudWatch
logs driver; a metric filter / EMF wrapper can be layered on later without touching call
sites.
"""

from __future__ import annotations

import json
import sys
import time


def emit(metric: str, **fields) -> None:
    line = {"metric": metric, "ts": time.time(), **fields}
    sys.stdout.write(json.dumps(line) + "\n")
    sys.stdout.flush()
