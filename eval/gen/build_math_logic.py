"""Build eval/drafts/math.json and eval/drafts/logic.json (50 items each).

Composition per category (D7): 22 set-A items (solver-dev, dev split only), 16 set-B items and
12 hand-written items (the test split is drawn only from B + hand). Difficulty is balanced ~50/50.
Run: .venv/Scripts/python.exe -m eval.gen.build_math_logic
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from eval.gen import hand_math_logic as H
from eval.gen import logic_gen, math_gen

OUT = Path(__file__).resolve().parents[1] / "drafts"

LOGIC_PLAN_A = ([(3, False, False)] * 3 + [(3, False, True)] * 3 + [(4, False, False)] * 3 + [(4, False, True)] * 2
                + [(5, True, False)] * 6 + [(5, True, True)] * 5)
LOGIC_PLAN_B = ([(3, False, False)] * 2 + [(3, False, True)] * 2 + [(4, False, False)] * 2 + [(4, False, True)] * 3
                + [(5, True, False)] * 3 + [(5, True, True)] * 4)


def finish(items, prefix, seed):
    random.Random(seed).shuffle(items)  # ids must not reveal the template set
    for i, it in enumerate(items, 1):
        it["id"] = f"{prefix}-{i:03d}"
        it["split"] = "unsplit"
        it["gold_checks"] = "independent re-computation" if prefix == "math" else "unique solution, 2 solvers"
    return items


def main():
    OUT.mkdir(exist_ok=True)
    math_items = (math_gen.generate("A", 11, 11, seed=101) + math_gen.generate("B", 8, 8, seed=202)
                  + H.hand_math_items())
    logic_items = (logic_gen.generate("A", LOGIC_PLAN_A, seed=303) + logic_gen.generate("B", LOGIC_PLAN_B, seed=404)
                   + H.hand_logic_items())
    for name, items, prefix, seed in (("math", math_items, "math", 7), ("logic", logic_items, "logic", 8)):
        assert len(items) == 50, (name, len(items))
        assert len({i["prompt"] for i in items}) == 50
        finish(items, prefix, seed)
        (OUT / f"{name}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
        from collections import Counter
        print(name, Counter((i["template_set"], i["difficulty"]) for i in items))


if __name__ == "__main__":
    main()
