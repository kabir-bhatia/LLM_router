"""Dev-only task loader. The test split is dropped at load time and asserted absent (D7, plan rule)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "eval" / "tasks_8cat.json"


def load_dev(path=TASKS_PATH) -> list:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    dev = [t for t in raw if t.get("split") == "dev"]
    del raw
    assert dev and all(t["split"] == "dev" for t in dev)
    return dev
