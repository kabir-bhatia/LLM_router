"""Phase 2 step 6: agreement of each judge with the hand labels, the D8 decision, eval/results/judge_decision.md.

Labels: the first word after `**Label:**` for each `## Item N` in judge_calibration_sheet.md (PASS/FAIL).
Verdicts: judge_calibration_key.json (written by eval.judge_calibration, rubric D10).
D8 rule: keep GLM (free) as the default judge if its agreement with the labels is >= 90% AND no more than
5 points below Qwen's; otherwise Qwen judges everything.
Run: .venv/Scripts/python.exe -X utf8 -m eval.judge_agreement
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "results" / "judge_calibration_sheet.md"
KEY = ROOT / "results" / "judge_calibration_key.json"
OUT = ROOT / "results" / "judge_decision.md"
JUDGES = ("glm", "qwen")


def parse_labels(text: str) -> dict:
    labels = {}
    for m in re.finditer(r"^## Item (\d+)\b.*?^\*\*Label:\*\*[ \t]*(\w+)", text, re.S | re.M):
        w = m.group(2).upper()
        if w in ("PASS", "FAIL"):
            labels[int(m.group(1))] = w == "PASS"
    return labels


def agreement(items: list, labels: dict, judge: str, pick=lambda it: True) -> tuple:
    sel = [it for it in items if pick(it)]
    ok = sum(it["verdicts"][judge]["passed"] == labels[it["item"]] for it in sel)  # None counts as disagreement
    return ok, len(sel)


def decide(glm: tuple, qwen: tuple) -> tuple:
    g, q = glm[0] / glm[1], qwen[0] / qwen[1]
    keep = g >= 0.90 and (q - g) <= 0.05 + 1e-9
    return ("glm" if keep else "qwen"), g, q


def pct(t) -> str:
    return f"{t[0]}/{t[1]} = {t[0] / t[1]:.0%}" if t[1] else "-"


def main():
    labels = parse_labels(SHEET.read_text(encoding="utf-8"))
    items = json.loads(KEY.read_text(encoding="utf-8"))
    assert len(labels) == len(items) == 40 and all(it["item"] in labels for it in items), (len(labels), len(items))
    models = sorted({it["model"] for it in items})
    cats = sorted({it["category"] for it in items})
    L = ["# Judge decision (Phase 2 step 6, D8 + D10)", "",
         f"{len(items)} calibration answers (dev split, factual + summaries, two answering models), hand labels: "
         f"{sum(labels.values())} PASS / {len(labels) - sum(labels.values())} FAIL. Judges ran with the D10 rubric "
         "(summaries: both core facts + nothing wrong; factual strict + popular-science clarification), blind, low reasoning effort.",
         "", "## Agreement with the hand labels", "", "| slice | n | GLM (hyde/glm-5.3-flash) | Qwen (qwen3p8-max) |", "|---|---|---|---|"]
    rows = [("overall", lambda it: True)]
    rows += [(f"category: {c}", (lambda c: lambda it: it["category"] == c)(c)) for c in cats]
    rows += [(f"answered by {m}", (lambda m: lambda it: it["model"] == m)(m)) for m in models]
    rows += [(f"label PASS", lambda it: labels[it["item"]]), (f"label FAIL", lambda it: not labels[it["item"]])]
    for name, pk in rows:
        a = {j: agreement(items, labels, j, pk) for j in JUDGES}
        L.append(f"| {name} | {a['glm'][1]} | {pct(a['glm'])} | {pct(a['qwen'])} |")
    glm, qwen = agreement(items, labels, "glm"), agreement(items, labels, "qwen")
    choice, g, q = decide(glm, qwen)
    L += ["", "## Disagreements with the labels", ""]
    for j in JUDGES:
        bad = [it for it in items if it["verdicts"][j]["passed"] != labels[it["item"]]]
        fp = sum(1 for it in bad if it["verdicts"][j]["passed"] is True)
        L.append(f"- **{j}**: {len(bad)} wrong ({fp} too lenient = judge PASS where label FAIL; {len(bad) - fp} too strict). "
                 "Items: " + ", ".join(f"{it['item']} ({it['task_id']}, {it['model']}, label {'PASS' if labels[it['item']] else 'FAIL'})"
                                       for it in bad))
    both = sum(it["verdicts"]["glm"]["passed"] == it["verdicts"]["qwen"]["passed"] for it in items)
    L += [f"- the two judges agree with each other on {both}/{len(items)}", "",
          "## Decision (D8 rule)", "",
          f"Rule: keep GLM if agreement >= 90% and no more than 5 points below Qwen. GLM {g:.1%}, Qwen {q:.1%} "
          f"(gap {100 * (q - g):+.1f} points, positive = Qwen better).", "",
          f"**Default judge: {'GLM (`hyde/glm-5.3-flash`, free)' if choice == 'glm' else 'Qwen (`qwen3p8-max`, Fireworks)'}**"
          + (", except that answers from a GLM model are judged by Qwen so no model grades itself." if choice == "glm"
             else " for everything."), "",
          f"Wired as `DEFAULT_JUDGE = \"{choice}\"` in `eval/graders/judge.py` and `eval/grade.py` (`--judge default`).",
          "", f"n = {len(items)}: one item is 2.5 points, so a gap of a few points is within noise; the rule is applied as written."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print("CHOICE", choice)


if __name__ == "__main__":
    main()
