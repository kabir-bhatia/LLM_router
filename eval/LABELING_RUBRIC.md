# Labeling Rubric

Ground-truth tier labels for `labeled_prompts.json`.

Every label in that file is assigned by hand against this rubric. This document
exists because "I labeled 100 prompts" is only a defensible result if the labels
follow a rule someone else could reapply and get the same answer. Without a
written rubric, the accuracy number in Phase 3 measures agreement with one
person's mood on one afternoon.

## The question a label answers

**Not** "how hard does this prompt look?" but:

> What is the *cheapest* tier that still produces an acceptable answer?

This framing matters. The router's job is cost control, so the ground truth has
to encode the cost/quality boundary, not a vibe about difficulty. A long prompt
is not automatically complex; a short one is not automatically simple.

## Tiers

### SIMPLE — mechanical transformation of given text

The answer is essentially *contained in* the prompt, and the model only has to
reshape it. Little world knowledge, no multi-step reasoning, low cost of a
mediocre answer.

- Translation, summarization, tone/format rewriting
- Extraction into a list or JSON from supplied text
- Single-fact lookup with an uncontroversial answer
- Grammar and spelling correction
- Classification into obvious given categories

*Test:* could a competent intern do this in under a minute with no context?

#### A note on lookup questions specifically

Prompts like *"Yes or no: does our free tier include API access?"* look like they
need a fact the model doesn't have — proprietary company policy, not something
Gemini was trained on. That's true, but it doesn't move the label, because it's
answering the wrong question.

The tier measures **reasoning demand assuming the necessary context is
available** — not whether the model currently has that context. Those are two
independent axes:

- **Reasoning demand** (what the tier is for): given the right facts, how much
  work is it to produce the answer? For a yes/no policy lookup, essentially
  none — SIMPLE.
- **Knowledge grounding** (a different problem entirely): does the model have
  the facts at all? A generic LLM doesn't know your company's free-tier terms
  regardless of size.

The reason these have to be kept separate: **escalating tier does not fix a
grounding problem.** `gemini-2.5-pro` doesn't know your internal policy docs
any better than `gemini-2.0-flash-lite` does — routing this prompt to COMPLEX
in the hope of a more correct answer would just spend more money for the same
hallucination risk. The actual fix is retrieval (RAG) or a system prompt
carrying the relevant doc, which is a different layer of the system than the
router and out of scope for this project.

Consequence for Phase 4: when prompts like this run through real generation
with no retrieval attached, the model will produce a plausible-sounding but
unverifiable — possibly fabricated — answer. That's expected and fine for
measuring routing/cost behavior, but it means Phase 4's results should be read
as "routed and billed correctly for the task's difficulty," not "answered
correctly." Don't let those two claims blur together in the write-up.

### MEDIUM — generation requiring real knowledge, single-threaded

Needs genuine domain knowledge or non-trivial generation, but follows one line
of reasoning to a well-defined answer. A wrong answer is visible and cheap to
correct.

- Explaining a concept to a stated audience
- Writing a self-contained function or script for a clear spec
- Comparing two named things on stated criteria
- Standard debugging of a short, complete snippet
- Drafting routine professional text

*Test:* one right answer, or a narrow band of right answers, reachable in one
pass.

### COMPLEX — multi-constraint reasoning where being wrong is expensive

Several constraints must be held simultaneously and traded off, or the reasoning
has multiple interacting steps where an early mistake silently corrupts the
result.

- System/architecture design under stated constraints
- Debugging where the cause is not local to the shown code
- Security analysis, threat modeling
- Non-obvious algorithm design or complexity work
- Ambiguous requirements that must be surfaced before answering
- Anything where a confident wrong answer costs real money or safety

*Test:* would a mediocre answer be *worse than no answer*, because it looks
right and isn't?

## Tie-breaking rules

Apply in order. These exist so that borderline cases resolve consistently
instead of by feel.

1. **Cost of a bad answer dominates.** If a plausible-but-wrong answer is
   expensive to detect, go up a tier. This is the single most important rule.
2. **Length is evidence, never a criterion.** A 2000-word prompt that says
   "summarize this" is SIMPLE. A 12-word prompt that says "why is my distributed
   lock occasionally releasing early?" is COMPLEX.
3. **Count the constraints.** Zero or one → SIMPLE/MEDIUM. Three or more that
   interact → COMPLEX.
4. **Do not label for the model you have.** Label the task, not what
   `gemini-2.0-flash-lite` happens to be good at. Otherwise the eval becomes
   circular and can only ever confirm the current setup.
5. **When genuinely torn, pick the cheaper tier and record it.** Set
   `"borderline": true`. Phase 3 accuracy should be reported both with and
   without borderline cases — a classifier that only fails on prompts *you*
   found ambiguous is a different story from one that fails on clear cases.

## Schema

```json
{
  "id": "sup-014",
  "prompt": "Translate the following support reply into Spanish: ...",
  "true_tier": "simple",
  "domain": "support",
  "borderline": false,
  "note": "pure translation, source text supplied"
}
```

| field | meaning |
|---|---|
| `id` | stable id, `<domain-prefix>-<nnn>`; never reuse after deletion |
| `prompt` | the prompt text exactly as sent to the router |
| `true_tier` | `simple` \| `medium` \| `complex` — your hand label |
| `domain` | `support` \| `codegen` \| `architecture` \| `summarization` \| `analysis` |
| `borderline` | true if rule 5 was invoked |
| `note` | one line on *why*, for the cases you'll be asked about |

Fill `note` for every borderline case and every COMPLEX label. Those are exactly
the rows an interviewer will point at, and "I don't remember why" is a bad
answer to a question about your own dataset.

## Balance targets

Aim for roughly even tiers and spread across domains, so that accuracy is not
inflated by a majority class:

| tier | target |
|---|---|
| simple | ~33% |
| medium | ~33% |
| complex | ~33% |

A classifier that always guesses one tier should score ~33%, not ~60%. That
makes the accuracy number mean something on its own.
