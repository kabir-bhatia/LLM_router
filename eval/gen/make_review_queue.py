"""Write eval/REVIEW_QUEUE.md: what the human must review before the dataset is frozen.

Contents: (1) every sentiment/factual/summarisation item where GLM disagreed or gave no usable answer,
(2) a 20% random sample (seeded) of the items where GLM agreed, (3) all hand-written NER items (gold depends
on stated conventions, not on computation). Items are grouped in batches of 10.
Run: .venv/Scripts/python.exe -X utf8 -m eval.gen.make_review_queue
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "drafts"
SEED = 2025


def load(cat):
    return json.loads((DRAFTS / f"{cat}.json").read_text(encoding="utf-8"))


def gold_text(it):
    g = it["gold"]
    c = it["category"]
    if c == "sentiment":
        return f"**{g['label']}**"
    if c == "factual":
        return f"Reference: {g['reference']}\n  Key points: " + "; ".join(g["key_points"])
    if c == "summarisation":
        return f"Constraint: `{g['constraints']}`\n  Key facts that must survive: " + "; ".join(g["key_facts"])
    if c == "ner":
        return "; ".join(f"{e['text']} = {e['type']}" for e in g["entities"])
    return str(g)


def render(it, glm, reason):
    quote = "\n".join("> " + ln for ln in it["prompt"].splitlines())
    out = [f"#### {it['id']}  ({it['category']}, {it['difficulty']}, phrasing: {it['phrasing']})",
           f"Why it is here: {reason}", "", quote, "",
           f"- **Gold:** {gold_text(it)}", f"- **Note:** {it['note'][:300]}"]
    if glm:
        gl = (glm.get("glm_answer") or "").strip().replace("\n", " ")
        out.append(f"- **GLM said:** {gl[:500]}")
        out.append(f"- **GLM check:** {str(glm.get('detail'))[:300]}")
        if glm.get("constraint_ok") is False:
            out.append(f"- GLM's own summary broke the constraint ({glm.get('constraint_detail')}): that is about GLM, not the gold.")
    out.append("- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`")
    out.append("")
    return "\n".join(out)


def main():
    rng = random.Random(SEED)
    glm = {r["id"]: r for r in json.loads((ROOT / "results" / "phase1_glm_check.json").read_text(encoding="utf-8"))}
    entries = []  # (item, glm_rec, reason)
    dis_n = agree_n = 0
    for cat in ("sentiment", "factual", "summarisation"):
        items = load(cat)
        dis = [i for i in items if glm.get(i["id"], {}).get("agree") is not True]
        ag = [i for i in items if glm.get(i["id"], {}).get("agree") is True]
        sample = rng.sample(ag, max(1, round(0.2 * len(ag))))
        dis_n += len(dis)
        agree_n += len(ag)
        entries += [(i, glm.get(i["id"]), "GLM disagrees (or no usable answer)") for i in dis]
        entries += [(i, glm.get(i["id"]), "random 20% sample of GLM-agreed items") for i in sample]
    ner = [i for i in load("ner") if i["source"] == "hand"]
    entries += [(i, None, "hand-written NER: gold depends on the stated span conventions") for i in ner]

    head = ["# Review queue (Phase 1, step 5)", "",
            "**You must review this before the dataset is frozen.** Nothing in `eval/tasks_8cat.json` exists yet;",
            "step 6 starts only after you answer. For each item tick one decision (or write the change).", "",
            "How to read it: *Gold* is what the grader will treat as the right answer. *Note* is the one-line",
            "reason. *GLM said* is an independent answer from glm-5.3-flash that never saw the gold.", "",
            "NER conventions to keep in mind: span = full proper name (\"Bank of America\" is one ORG); titles",
            "(\"Dr.\") and possessive 's are not part of a span; DATE = explicit dates, month-year or year only.", "",
            "What the disagreements look like: 2 sentiment items are genuinely ambiguous (neutral vs a reading of",
            "the quoted word as negative/positive); the factual ones are mostly GLM leaving out a key point (or",
            "adding an unlisted figure); the summary ones are almost all GLM leaving out one of the key facts under a",
            "tight word limit. That second kind may mean my key-fact lists are too demanding for the limit: if you",
            "think so, answer 'drop key fact N' on that item rather than changing the passage.", "",
            f"Totals: {len(entries)} items = {dis_n} GLM disagreements + {len(entries) - dis_n - len(ner)} sampled agreements"
            f" (of {agree_n}) + {len(ner)} hand-written NER items.", ""]
    body, bn = [], 0
    for k in range(0, len(entries), 10):
        bn += 1
        chunk = entries[k:k + 10]
        body.append(f"## Batch {bn} ({len(chunk)} items)\n")
        body += [render(*e) for e in chunk]
    (ROOT / "REVIEW_QUEUE.md").write_text("\n".join(head + body), encoding="utf-8")
    print(f"{len(entries)} items in {bn} batches; disagreements={dis_n}")


if __name__ == "__main__":
    main()
