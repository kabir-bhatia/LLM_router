"""D2: choose B1 (best single API model) and B2 (cheapest sufficient API model) from dev results. Nothing is chosen by hand.

Usage: python -m eval.phase4.pick_baselines [--scores FILE ...] [--out eval/results/phase4/baselines.json]
"""
import argparse
import json

from eval.phase4.io_phase3 import load_results
from eval.phase4.policy_lib import api_models, pick_baselines
from router.data import ROOT, load_dev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", nargs="*", default=None)
    ap.add_argument("--out", default=str(ROOT / "eval" / "results" / "phase4" / "baselines.json"))
    a = ap.parse_args(argv)
    tasks = load_dev()
    results, kinds, files = load_results(a.scores)
    api = api_models(kinds)
    assert len(api) >= 2, f"need API results; found models {sorted(kinds)}"
    n_expected = len(tasks)
    for m in api:
        n = sum(1 for t in tasks if (m, t["id"]) in results)
        assert n == n_expected, f"{m} has {n}/{n_expected} dev answers graded; Phase 3 is not complete"
    pending = [k for k, v in results.items() if v["passed"] is None]
    assert not pending, f"{len(pending)} answers still ungraded (judge pending)"
    out = pick_baselines(tasks, results, kinds)
    out["score_files"] = [str(f) for f in files]
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("B1", "B2")}, indent=1))


if __name__ == "__main__":
    main()
