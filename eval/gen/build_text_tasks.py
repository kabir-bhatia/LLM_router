"""Build eval/drafts/{sentiment,factual,summarisation}.json from the hand-written item files.

Gold checks here are structural (balanced labels, key facts present in the source passage, constraint
satisfiable by the passage's own first sentence length etc.). The independent GLM answer check runs
in eval/gen/glm_check.py and its disagreements go to eval/REVIEW_QUEUE.md.
Run: .venv/Scripts/python.exe -m eval.gen.build_text_tasks
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from eval.gen import items_sentiment_factual as SF
from eval.gen import items_summary as SU
from eval.gen import summary_core as SC
from eval.gen.items_summary_extra import EXTRAS
from eval.gen.items_summary_refs import REFS
from eval.gen import factual_audit
from eval.graders.constraint import check_constraints, summary_text

OUT = Path(__file__).resolve().parents[1] / "drafts"


def finish(items, prefix, seed):
    random.Random(seed).shuffle(items)
    for i, it in enumerate(items, 1):
        it["id"] = f"{prefix}-{i:03d}"
        it["split"] = "unsplit"
    return items


def build_sentiment():
    rng = random.Random(41)
    items = []
    for text, label, diff, kind, note in SF.SENTIMENT:
        style, tpl = rng.choice(SF.SENT_PROMPTS)
        items.append(dict(prompt=tpl.format(kind=kind, t=text), category="sentiment", grader="label",
                          gold={"label": label, "text": text}, source="hand", difficulty=diff, phrasing=style,
                          note=note, gold_checks="Claude draft; GLM agreement check pending"))
    return items


def build_factual():
    rng = random.Random(42)
    items = []
    for q, ref, kps, diff, dom in SF.FACTUAL:
        style, tpl = rng.choice(SF.FACT_WRAPS)
        ql = q[0].lower() + q[1:]
        req, opt = factual_audit.split(q, kps)
        items.append(dict(prompt=tpl.format(q=q, ql=ql), category="factual", grader="judge",
                          gold={"reference": ref, "key_points": req, "optional_points": opt, "question": q}, source="hand",
                          difficulty=diff, phrasing=style, domain=dom,
                          note=f"Reference: {ref}", gold_checks="Claude draft; GLM agreement check pending"))
    factual_audit.audit_log([(q, k) for q, _, k, _, _ in SF.FACTUAL])  # asserts every item was audited
    return items


def instr(c):
    kind, n = c
    return {("sentences", 1): "in exactly one sentence", ("sentences", 2): "in exactly two sentences",
            ("bullets", 3): "as exactly 3 bullet points (each line starting with '- ')"}.get(
        c, f"in no more than {n} words" if kind == "max_words" else None)


WRAPS = [
    ("imperative", "Summarise the following text {ins}:\n\n{p}"),
    ("tldr", "{p}\n\nTL;DR {ins}, please."),
    ("embedded", "Here's an article my manager sent me. Can you summarise it {ins}? I only have a minute.\n\n{p}"),
    ("careful", "Condense this passage {ins}. Keep only facts stated in the text.\n\n\"{p}\""),
]


def build_summary():
    rng = random.Random(43)
    items = []
    assert len(EXTRAS) == len(SU.ITEMS) == len(REFS), (len(EXTRAS), len(SU.ITEMS), len(REFS))
    assert len(SC.CORE) == len(SU.ITEMS)
    for (passage, cons, facts, hints, diff), extra, ref, core in zip(SU.ITEMS, EXTRAS, REFS, SC.CORE):
        low = passage.lower()
        c1, h1, c2, h2, secondary = core
        for f, hs in zip(facts, hints):
            assert any(h.lower() in low for h in hs), f"fact hint not in passage: {facts} / {hs}"
        assert len(facts) == len(hints)
        passage = passage + " " + extra
        assert 105 <= len(passage.split()) <= 250, len(passage.split())
        style, tpl = rng.choice(WRAPS)
        kind, n = cons
        # the reference summary must satisfy the constraint and contain every required key fact
        ok, problems = check_constraints(summary_text(ref), {kind: n})
        assert ok, f"reference violates constraint {cons}: {problems}: {ref}"
        rlow = ref.lower()
        for f, hs in zip(facts, hints):
            assert any(h.lower() in rlow for h in hs), f"reference misses fact {f!r}: {ref}"
        for c, h in ((c1, h1), (c2, h2)):  # D10: the reference must contain both core facts
            assert h.lower() in rlow, f"reference misses core fact {c!r} (hint {h!r}): {ref}"
        if kind == "max_words" and n <= 25:
            assert len(facts) <= 3, "max 3 required key facts for limits <= 25 words"
        words = len(passage.split())
        core_facts = [c1, c2]
        items.append(dict(
            prompt=tpl.format(ins=instr(cons), p=passage), category="summarisation", grader="constraint",
            gold={"constraints": {kind: n}, "key_facts": facts, "fact_hints": hints,
                  "core_facts": core_facts, "secondary_facts": secondary, "source_text": passage,
                  "reference_summary": ref},
            source="hand", difficulty=diff, phrasing=style, passage_words=words,
            note="Constraint is checked by code; key facts (" + "; ".join(facts) + ") must survive and nothing may be invented (blind judge).",
            gold_checks="key-fact keywords found in passage; GLM agreement check pending"))
    return items


def main():
    OUT.mkdir(exist_ok=True)
    for name, items, prefix, seed in (("sentiment", build_sentiment(), "sent", 5), ("factual", build_factual(), "fact", 6),
                                      ("summarisation", build_summary(), "summ", 7)):
        assert len(items) == 50, (name, len(items))
        assert len({i["prompt"] for i in items}) == 50
        finish(items, prefix, seed)
        (OUT / f"{name}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
        extra = Counter(i["gold"].get("label") for i in items) if name == "sentiment" else ""
        print(name, Counter(i["difficulty"] for i in items), Counter(i["phrasing"] for i in items), extra)
    s = json.loads((OUT / "summarisation.json").read_text(encoding="utf-8"))
    w = [i["passage_words"] for i in s]
    print("summary passage words min/median/max", min(w), sorted(w)[25], max(w))


if __name__ == "__main__":
    main()
