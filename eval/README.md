# Phase 2 — Labeling Workflow

## Files

| File | Purpose |
|---|---|
| `LABELING_RUBRIC.md` | The rule you're applying — read this first |
| `candidate_prompts.json` | 108 unlabeled candidates, `true_tier: null` |
| `labeled_prompts.json` | **What you produce.** Same schema, `true_tier` filled in |

## Why 108 and not the ~80-120 the plan called for

Balanced across domains except summarization, which is deliberately lighter (12
vs. 24) — summarization prompts skew SIMPLE/MEDIUM almost by construction (the
answer is mostly given in the prompt), so padding it to 24 would have pulled the
whole set's SIMPLE tier disproportionately from one domain instead of spreading
across domains. You can trim further, or ask for another batch in a different
domain, once you see how the labeling goes.

## How to label

1. Open `candidate_prompts.json`.
2. For each row, read the prompt and apply the rubric's core question: **what's
   the cheapest tier that still gives an acceptable answer** — not "how hard
   does this look."
3. Set `"true_tier"` to `"simple"`, `"medium"`, or `"complex"`.
4. If you're genuinely torn between two tiers, pick the cheaper one and set
   `"borderline": true`. Phase 3 will report accuracy both with and without
   borderline cases.
5. Fill `"note"` for every COMPLEX label and every borderline case — one line on
   *why*. These are exactly the rows an interviewer will ask about.
6. Save the result as `labeled_prompts.json` (don't overwrite the candidates
   file — keep the unlabeled version so the split is auditable later).

Editing raw JSON by hand is fine for 108 rows, but if you'd rather work in a
spreadsheet: import the file, edit the `true_tier` and `note` columns, export
back to JSON with the same field names.

## A few prompts were built as traps — on purpose

The rubric says length is evidence, never a criterion.

- **Short but complex**: `code-005` — one sentence, but debugging a subtle
  concurrency bug with no local root cause. Landed at COMPLEX despite the short
  prompt.
- **Long but not complex**: `sup-002`, `sup-019` — multi-clause prompts that
  turned out to land at MEDIUM, not SIMPLE, once actually labeled. (An earlier
  draft of this doc claimed they were "long but simple" — that was wrong; they
  each carry a real single-pass judgment call, `sup-002`'s multi-part reply and
  `sup-019`'s cross-jurisdiction legal-term flagging. Corrected here rather than
  left stale, since a labeling doc that misdescribes its own dataset is worse
  than no commentary at all.)
- `anal-006` (arithmetic) is a plain SIMPLE control, not a trap.

If a classifier's predictions end up correlating strongly with prompt *length*
rather than the rubric's actual criteria, that's worth calling out explicitly in
Phase 3 — the rule-based classifier literally thresholds on token count, so it
could look accurate on this dataset for the wrong reason, which is a more
interesting finding than either accuracy number alone.

## Status

**Labeled** — `eval/labeled_prompts.json` exists. It was drafted by Claude at
the user's explicit direction, applying `LABELING_RUBRIC.md` consistently
across all 108 prompts (source: `scripts/apply_phase2_labels.py`), not
hand-labeled by the user prompt-by-prompt. Every COMPLEX and every borderline
label carries a `note` explaining the reasoning, specifically so it can be
reviewed and defended (or overridden) rather than taken on faith.

Tier distribution came out 55% simple / 14% medium / 31% complex — skewed away
from the rubric's ~33/33/33 target. That's a property of the prompts as
written, not something corrected after the fact by picking whichever tier hits
quota; forcing balance that way would corrupt the one thing this dataset is
supposed to be honest about. Two ways to handle it in Phase 3: report
macro-averaged accuracy (per-class recall, averaged) instead of raw accuracy so
the majority SIMPLE class doesn't dominate the headline number, and/or write a
supplemental batch weighted toward MEDIUM if a more balanced set is wanted.

**Before using this for the CV/interview claim**, read through
`labeled_prompts.json` and adjust anything that doesn't match your own
judgment — the value of hand-labeling is being able to defend *why* a given
prompt is COMPLEX when asked, and that only holds if the label is one you'd
actually give.

## When you're done

Run the accuracy eval (Phase 3, not yet built) against `labeled_prompts.json`.
