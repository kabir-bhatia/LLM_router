"""Write eval/results/phase1_report.md from the freeze summary and the other result files."""

import json
from pathlib import Path

from eval.gen import factual_audit as FA
from eval.gen import items_sentiment_factual as SF

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "phase1_freeze_summary.json").read_text(encoding="utf-8"))
D = json.loads((ROOT / "results" / "phase1_dedup.json").read_text(encoding="utf-8"))
G = json.loads((ROOT / "results" / "phase1_glm_check.json").read_text(encoding="utf-8"))
CATS = ["factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen"]

rows = []
for c in CATS:
    v = [S["cells"][f"{c}|{d}|{s}"] for d in ("easy", "hard") for s in ("dev", "test")]
    rows.append(f"| {c} | {v[0]} | {v[1]} | {v[2]} | {v[3]} | {sum(v)} |")
agree = {}
for c in ("sentiment", "factual", "summarisation"):
    rs = [r for r in G if r["category"] == c]
    agree[c] = (sum(1 for r in rs if r["agree"] is True), len(rs))
ts_rows = []
for c in ("math", "logic"):
    for ts in ("A", "B", "hand"):
        ts_rows.append(f"| {c} | {ts} | {S['template_sets'].get(f'{c}|{ts}|dev', 0)} | {S['template_sets'].get(f'{c}|{ts}|test', 0)} |")
chk_rows = [f"| {c['check']} | {c['checked']} | {c['failed']} |" for c in S["checks"]]
audit = FA.audit_log([(q, k) for q, _, k, _, _ in SF.FACTUAL])
dd = "; ".join(f"{k}: max sim {v['max_similarity']}, flagged {len(v['flagged_pairs'])}" for k, v in D["by_category"].items())

md = f"""# Phase 1 report: the 8-category eval dataset

Frozen file: `eval/tasks_8cat.json`, 400 tasks, sha256 `{S['sha256']}`.
Built by `eval/gen/` (generators, item files, `freeze.py`), graded by `eval/graders/`. Split seed {20251120}.
API spend: $0 (only the free `hyde/glm-5.3-flash` was called, ~400 calls). No Fireworks or Gemini calls.

## Counts per category x difficulty x split

Test is 10 of 25 per cell (40%), dev 15 (60%); every test cell has 10 items (requirement: >= 8).

| category | easy dev | easy test | hard dev | hard test | total |
|---|---|---|---|---|---|
{chr(10).join(rows)}

Math and logic (D7): all set-A items are dev; the test split holds only set-B and hand-written items.

| category | template set | dev | test |
|---|---|---|---|
{chr(10).join(ts_rows)}

Consequence for Phase 4: solvers may be tuned on the 22 set-A items per category (plus the 8 dev items
from set B / hand-written, which were not used to build solvers and can serve as a validation set).

## Verification results

| check | items | failures |
|---|---|---|
{chr(10).join(chk_rows)}

- Near-duplicates: MiniLM embedding cosine >= 0.95 flagged 3 pairs ({dd}). All three are the same
  template with different numbers/dates and different gold (math-001/math-010, math-002/math-013,
  ner-011/ner-048), so none are true duplicates; they are kept.
- Independent GLM agreement (glm-5.3-flash answered blind; free): sentiment {agree['sentiment'][0]}/{agree['sentiment'][1]},
  factual {agree['factual'][0]}/{agree['factual'][1]} (was 47/50 before the judge rubric fix), summarisation
  {agree['summarisation'][0]}/{agree['summarisation'][1]}. The 10 summary disagreements are GLM leaving out a required fact
  under a tight limit; the reviewer ruled the gold fine. GLM judging its own factual answers is a known bias,
  so agreement is a screen only; the human review is the verification.
- Human review: the parent session reviewed `eval/REVIEW_QUEUE.md` on Kabir's behalf (not Kabir directly).
  Kabir should still skim the decisions below before Phase 2 relies on the data.

## Review decisions applied

Item decisions:
- sent-010 (ambiguous triage note): dropped and replaced by an unambiguous neutral review (hard, embedded phrasing); GLM agrees.
- fact-006: gold kept (the FAIL was a judge-rubric problem). fact-013: kept; "nothing with mass can reach c" is now optional. fact-046: kept; "distributed/hierarchical lookup" now optional.
- summ-016 (Haldane): dropped the "three teams over four months" fact. summ-040 (railway): facts are now closed 1966 / 9 of 24 km / 4 million more for the bridge (volunteers and steam dropped). summ-047 (Norvia): dropped the poll fact.
- summ-017, -021, -029, -032, -037, -038, -049: gold kept (GLM omitted a fact that fits the limit).
- ner-006: Kenya accepted as LOCATION or ORG. ner-008: accepted "AIIMS Delhi"=ORG, or "AIIMS"=ORG plus "Delhi"=LOCATION. Other hand-written NER items kept.
- All 27 sampled agreements: gold kept.

Systemic fixes:
1. Judge rubric (`eval/graders/judge.py`): FAIL only for wrong/contradicting claims or a missing REQUIRED key point; correct extra detail never fails. Applies to factual and summaries.
2. Factual: every item's key points split into `key_points` (required) and `optional_points`. Audit of all 50 items; moved to optional:
{chr(10).join(audit)}
   Unchanged (all points required): {len(FA.KEPT_ALL)} items.
3. Summarisation: every item has a written `reference_summary`; the freeze fails unless it meets the constraint and contains each required fact (checked by code). Limits <= 25 words have at most 3 required facts (the 3 trimmed items now have 2-3).
4. NER: gold supports `alternatives` (full alternative readings); the grader strips titles from PERSON spans and a trailing possessive 's before matching. Self-tests added.
5. Split follows the D7 rule above, with every test cell >= 8 (all are 10); no extra set-B items were needed.

## Post-freeze amendments (Phase 2, before anything was graded)

Agreed with Kabir; made at the source (`eval/gen/factual_audit.py`), then `build_text_tasks` and `freeze` re-run (all checks pass, split unchanged, only two tasks differ):
- fact-028 (sky blue, not violet): "violet is scattered more strongly than blue" is REQUIRED again (it is the point of the question).
- fact-001 (Peace of Westphalia): "established state sovereignty principles" is REQUIRED again.
sha256 of `eval/tasks_8cat.json` after these two fixes: `92d5b5bdc109718b4786ec0349b15a5842320ea5fe64af60bff326c7a9e67a8f` (was `31afd1b22b348278b13593cb3f547cf1fa3de0f1888945ee3a58bc0037391c6f`).
The audit list below therefore shows 2 fewer moved-to-optional items than before.

D10 amendment (summaries; agreed 2026-11-20 after the judge calibration, still before any benchmark grading): every one of the 50
summarisation tasks now has exactly 2 `core_facts` (the headline and its main "but"/consequence, each ONE idea in plain words) and a list of
`secondary_facts` (the detail). `key_facts`/`fact_hints` are unchanged (legacy), so only the 50 summarisation tasks gained these two keys, and
the dev/test split is identical. Round 1 of the split (the first two old key facts) was too coarse, bundling several sub-facts, and made the
judges too strict, so it was replaced by round 2 before any benchmark grading (sha256 of round 1: `2bf21ea7066fb28b00a69f0088b0fa709234875cf658e740e93effb46fe6aa2d`).
Source of truth: `eval/gen/summary_core.py` (core text, a reference-hint phrase per core fact, secondary list), applied in
`eval/gen/build_text_tasks.py`, which asserts every `reference_summary` contains both core facts. The 50 pairs are listed in `eval/results/summary_core_facts.md`.
**Final sha256 of `eval/tasks_8cat.json`: `{S['sha256']}`.**

## Known weak spots (be honest about these in the interview)

- Easy items are easy for strong models; the value is in the hard half and in the dev/test separation. Hard items are only "hard" by my labelling until Phase 3 measures it.
- Phrasing is skewed: math is 23/50 `word_problem`, only 4 `imperative` and 2 `formal`; NER is 21/50 `casual`. The classifier test (Phase 5) has less coverage of those styles.
- Templated near-clones exist (same template, different numbers; some, like math-013 with two equal speeds, are trivial variants).
- Factual and summary gold are Claude-drafted with a GLM screen and a parent-session review, not independent human experts; the factual reference answers could contain subtle errors.
- Summary passages are 111-152 words (plan: 120-250); about 10 are under 120. Key-fact lists were tight under small word limits.
- Code items are in the style of well-known exercises (gcd, fizzbuzz, two-sum, edit distance); models may have seen close variants, so code scores may be optimistic. Hidden tests are 5-10 asserts per task; they were checked against the reference only, so a test and reference could share a misreading of the spec.
- Logic puzzles are permutation puzzles with 3-5 entities only; they say little about other deduction styles. The 12 hand-written ones cover knights/knaves, conditionals and two-attribute puzzles.
- Sentiment `neutral` and `mixed` boundaries are judgement calls (stated in the notes); ner has span conventions (full proper name; no titles; no possessive; DATE = explicit dates or years).
- The dedup check is within a category only and by embedding similarity; it does not detect memorised public items.
- Windows note: `platform.uname()` hangs on this machine (WMI); `tests/conftest.py`, `eval/gen/dedup_check.py` work around it.

## Reproduce

`.venv/Scripts/python.exe -X utf8 -m eval.gen.build_math_logic`, `eval.gen.build_code_tasks`, `eval.gen.build_text_tasks`,
then `eval.gen.freeze` and `eval.gen.write_report` (run from the repo root with `PYTHONPATH=.`). Tests: `pytest eval tests`.
"""
(ROOT / "results" / "phase1_report.md").write_text(md, encoding="utf-8")
print("report written", len(md))
