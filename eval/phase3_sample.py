"""Fixed 40-task dev sample (5 per category) for the Phase 3 CPU-latency run.

Seeded, so it is reproducible: 2 easy + 2 hard + 1 random from the remaining dev tasks per category.
Writes eval/results/phase3/cpu_sample_ids.json. Dev tasks only.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 20261120


def pick():
    tasks = json.loads((ROOT / "tasks_8cat.json").read_text(encoding="utf-8"))
    dev = [t for t in tasks if t["split"] == "dev"]
    rng = random.Random(SEED)
    ids = []
    for c in sorted({t["category"] for t in dev}):
        pool = sorted((t for t in dev if t["category"] == c), key=lambda t: t["id"])
        easy = [t["id"] for t in pool if t["difficulty"] == "easy"]
        hard = [t["id"] for t in pool if t["difficulty"] == "hard"]
        chosen = rng.sample(easy, 2) + rng.sample(hard, 2)
        rest = [t["id"] for t in pool if t["id"] not in chosen]
        chosen.append(rng.choice(rest))
        ids += sorted(chosen)
    return ids


if __name__ == "__main__":
    ids = pick()
    assert len(ids) == 40 and len(set(ids)) == 40
    out = ROOT / "results" / "phase3" / "cpu_sample_ids.json"
    out.write_text(json.dumps({"seed": SEED, "rule": "per category: 2 easy, 2 hard, 1 random from the rest", "ids": ids}, indent=1), encoding="utf-8")
    print("wrote", out, len(ids))
