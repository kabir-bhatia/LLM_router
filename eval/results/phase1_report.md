# Phase 1 report: the 8-category eval dataset

Frozen file: `eval/tasks_8cat.json`, 400 tasks, sha256 `7246113c34a9cc6bdf58cdcbc44f7665bacd1cc41100ccf7f346d98400462344`.
Built by `eval/gen/` (generators, item files, `freeze.py`), graded by `eval/graders/`. Split seed 20251120.
API spend: $0 (only the free `hyde/glm-5.3-flash` was called, ~400 calls). No Fireworks or Gemini calls.

## Counts per category x difficulty x split

Test is 10 of 25 per cell (40%), dev 15 (60%); every test cell has 10 items (requirement: >= 8).

| category | easy dev | easy test | hard dev | hard test | total |
|---|---|---|---|---|---|
| factual | 15 | 10 | 15 | 10 | 50 |
| math | 15 | 10 | 15 | 10 | 50 |
| sentiment | 15 | 10 | 15 | 10 | 50 |
| summarisation | 15 | 10 | 15 | 10 | 50 |
| ner | 15 | 10 | 15 | 10 | 50 |
| code_debug | 15 | 10 | 15 | 10 | 50 |
| logic | 15 | 10 | 15 | 10 | 50 |
| code_gen | 15 | 10 | 15 | 10 | 50 |

Math and logic (D7): all set-A items are dev; the test split holds only set-B and hand-written items.

| category | template set | dev | test |
|---|---|---|---|
| math | A | 22 | 0 |
| math | B | 6 | 10 |
| math | hand | 2 | 10 |
| logic | A | 22 | 0 |
| logic | B | 6 | 10 |
| logic | hand | 2 | 10 |

Consequence for Phase 4: solvers may be tuned on the 22 set-A items per category (plus the 8 dev items
from set B / hand-written, which were not used to build solvers and can serve as a validation set).

## Verification results

| check | items | failures |
|---|---|---|
| schema valid (all required fields, grader matches category) | 400 | 0 |
| unique ids | 400 | 0 |
| unique prompts (exact) | 400 | 0 |
| 25 easy + 25 hard per category | 8 | 0 |
| gold answers pass their own grader (math, logic, sentiment, NER incl. alternatives; NER spans occur in prompt) | 200 | 0 |
| code_gen: reference passes all hidden tests (re-run) | 50 | 0 |
| code_debug: tests pass on reference and fail on the buggy code shown in the prompt (re-run) | 50 | 0 |
| tests per task | 100 | 0 |
| math: regeneration reproduces every prompt+gold (independent recomputation / unique-solution asserts re-run) | 50 | 0 |
| logic: regeneration reproduces every prompt+gold (independent recomputation / unique-solution asserts re-run) | 50 | 0 |
| summarisation: reference_summary meets constraint and contains every required key fact | 50 | 0 |
| factual: every item has >=1 required key point | 50 | 0 |
| sentiment: labels balanced (13/13/12/12) | 50 | 0 |

- Near-duplicates: MiniLM embedding cosine >= 0.95 flagged 3 pairs (factual: max sim 0.842, flagged 0; math: max sim 0.96, flagged 2; sentiment: max sim 0.826, flagged 0; summarisation: max sim 0.671, flagged 0; ner: max sim 0.951, flagged 1; code_debug: max sim 0.769, flagged 0; logic: max sim 0.931, flagged 0; code_gen: max sim 0.801, flagged 0). All three are the same
  template with different numbers/dates and different gold (math-001/math-010, math-002/math-013,
  ner-011/ner-048), so none are true duplicates; they are kept.
- Independent GLM agreement (glm-5.3-flash answered blind; free): sentiment 50/50,
  factual 50/50 (was 47/50 before the judge rubric fix), summarisation
  40/50. The 10 summary disagreements are GLM leaving out a required fact
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
- What does DNS do? -> optional: works as a distributed/hierarchical lookup system
- What is the difference between a virus and a bacterium? -> optional: antibiotics treat bacteria, not viruses
- Why does the Moon have phases? -> optional: not caused by Earth's shadow
- Explain what an API is. -> optional: hides the implementation
- What was the Industrial Revolution? -> optional: urbanisation / social change
- How do vaccines work? -> optional: faster response on later exposure
- What is compound interest? -> optional: grows faster/exponentially vs simple interest
- What causes the seasons on Earth? -> optional: not distance from the Sun
- What was the French Revolution? -> optional: ideals of liberty/equality or republic
- What is the greenhouse effect? -> optional: increased by human greenhouse-gas emissions
- What is a black hole? -> optional: boundary called the event horizon
- Explain the water cycle. -> optional: collection in oceans, rivers, lakes and groundwater
- What do mitochondria do in a cell? -> optional: through cellular respiration
- What was the Cold War? -> optional: ended around 1991
- Does the Coriolis effect decide which way water spins down a bathtub drain? -> optional: basin shape / initial motion dominate; matters for large systems like cyclones
- What were the main causes of the 2008 global financial crisis? -> optional: collapse of institutions such as Lehman Brothers
- How does public-key cryptography let two strangers communicate securely? -> optional: no prior shared secret needed
- What does the Heisenberg uncertainty principle say? -> optional: fundamental to quantum mechanics, not instrument clumsiness
- When and how did the Western Roman Empire end? -> optional: Eastern Empire survived until 1453
- What is the difference between correlation and causation? -> optional: confounders/coincidence can explain correlation
- How does the attention mechanism in a transformer model work? -> optional: uses queries, keys and values; captures long-range dependencies in parallel
- What is the difference between a recession and a depression? -> optional: depression has no formal precise definition
- Why does ice float on liquid water? -> optional: hydrogen bonds form an open lattice when freezing
- What was the significance of the Magna Carta of 1215? -> optional: precursor of constitutional rights
- How do mRNA vaccines work? -> optional: mRNA degrades and does not alter DNA
- What is opportunity cost? -> optional: arises from scarcity/choice
- Why is the speed of light central to special relativity? -> optional: nothing with mass can reach/exceed it
- What caused the Dust Bowl in the 1930s United States? -> optional: wind erosion and dust storms on the Great Plains
- What is a hash function, and why is that useful for storing passwords? -> optional: salting the hash
- How does a heat pump work, and why can it deliver more heat than the electrical energy it uses? -> optional: moves heat using a refrigerant cycle
- What is the difference between nominal and real interest rates? -> optional: real rate shows change in purchasing power
- What is a race condition in programming? -> optional: prevented by locks/atomics/synchronisation
   Unchanged (all points required): 18 items.
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
**Final sha256 of `eval/tasks_8cat.json`: `7246113c34a9cc6bdf58cdcbc44f7665bacd1cc41100ccf7f346d98400462344`.**

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
