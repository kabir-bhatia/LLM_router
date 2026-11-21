"""Run the router validators over the real Phase 2 dev-split local answers and compare with the grader scores.
Reports, per category: share of answers the validator accepts, accuracy of accepted answers vs rejected answers,
and 'false rejects' (correct answers the validator would have escalated). Dev only."""
import json
from collections import defaultdict
from pathlib import Path

from router.data import ROOT, load_dev
from router.validators import validate

d = ROOT / "eval" / "results" / "phase2_dryrun"
dev = {t["id"]: t for t in load_dev()}
ans = [json.loads(x) for x in (d / "answers_dryrun.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
sc = [json.loads(x) for x in (d / "answers_dryrun_scores.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
assert len(ans) == len(sc)
stats = defaultdict(lambda: defaultdict(int))
for a, s in zip(ans, sc):
    t = dev[a["task_id"]]  # KeyError if a test task sneaks in
    v = validate(t["category"], t["prompt"], a["raw_text"])
    ok = s.get("passed")
    st = stats[t["category"]]
    st["n"] += 1
    if ok is None:
        st["ungraded"] += 1
        continue
    st["graded"] += 1
    st["accept" if v.ok else "reject"] += 1
    st["accept_correct"] += bool(v.ok and ok)
    st["reject_correct"] += bool((not v.ok) and ok)
    st["correct"] += bool(ok)
lines = ["| category | graded | validator accepts | correct among accepted | rejected | correct among rejected (false escalations) |",
         "|---|---|---|---|---|---|"]
for c, st in sorted(stats.items()):
    lines.append(f"| {c} | {st['graded']} | {st['accept']} | {st['accept_correct']} | {st['reject']} | {st['reject_correct']} |")
out = "\n".join(lines)
print(out)
(ROOT / "eval" / "results" / "phase4" / "validator_check.md").write_text(
    "# Validators vs real dev answers (gemma3:1b + qwen3:1.7b, Phase 2 dry run)\n\n"
    "Graded answers only (answers pending the judge are skipped; the dry-run score file predates the judge).\n\n" + out + "\n", encoding="utf-8")
