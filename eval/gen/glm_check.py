"""Independent-answer agreement check with hyde/glm-5.3-flash (free; D3/D8 plan step 4).

For sentiment, factual and summarisation drafts GLM answers WITHOUT seeing the gold. Then:
  sentiment     : GLM's label vs gold label                        -> agree / disagree
  factual       : GLM judges its own answer against the reference  -> PASS = agree
  summarisation : GLM writes the summary; GLM judge checks the key facts survive and nothing is invented
Disagreements (and unparseable outputs) go to eval/REVIEW_QUEUE.md. Results: eval/results/phase1_glm_check.json
(GLM judging its own factual answers is a known bias: agreement is only a screen, the human review decides.)
Run: .venv/Scripts/python.exe -X utf8 -m eval.gen.glm_check
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from eval.graders import grade
from eval.graders.formats import FORMAT_INSTRUCTIONS
from eval.graders.judge import build_judge_prompt, parse_verdict
from src.providers.openai_compat import OpenAICompatProvider

MODEL = "hyde/glm-5.3-flash"
ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "drafts"
OUT = ROOT / "results" / "phase1_glm_check.json"


async def ask(p, prompt, system=None, max_tokens=1800, tries=4):
    for k in range(tries):
        try:
            r = await p.generate(prompt, MODEL, max_tokens=max_tokens, temperature=0.0, system=system,
                                 extra={"reasoning_effort": "low"})
            if r.text.strip():
                return r.text
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
            await asyncio.sleep(3 * (k + 1))
    return ""


async def check_item(p, sem, it, old_ans=None):
    async with sem:
        cat = it["category"]
        system = FORMAT_INSTRUCTIONS[cat]
        ans = (old_ans or {}).get(it["id"]) or await ask(p, it["prompt"], system)
        rec = {"id": it["id"], "category": cat, "glm_answer": ans}
        if not ans:
            rec.update(agree=None, detail="empty GLM answer")
        elif cat == "sentiment":
            r = grade({"grader": "label", "gold": it["gold"]}, ans)
            rec.update(agree=bool(r.passed), detail=f"GLM label={r.extracted}, gold={it['gold']['label']}")
        elif cat == "factual":
            jp = build_judge_prompt(it["gold"]["question"], it["gold"]["reference"], it["gold"]["key_points"], ans,
                                    optional=it["gold"].get("optional_points"))
            v = await ask(p, jp, max_tokens=600)
            verdict = parse_verdict(v)
            rec.update(agree=verdict, detail=v.strip()[:300], judge_raw=v.strip()[:300])
        else:  # summarisation
            g = it["gold"]
            cons = grade({"grader": "constraint", "gold": g}, ans)
            jp = build_judge_prompt("Summarise the source text under the stated constraint.", g["source_text"],
                                    g["key_facts"], ans)
            v = await ask(p, jp, max_tokens=600)
            verdict = parse_verdict(v)
            rec.update(agree=verdict, detail=v.strip()[:300], constraint_ok=cons.meta.get("constraint_ok"),
                       constraint_detail=cons.detail)
        return rec


async def main():
    p = OpenAICompatProvider.hyde(timeout=180)
    sem = asyncio.Semaphore(4)
    items = []
    for cat in ("sentiment", "factual", "summarisation"):
        items += json.loads((DRAFTS / f"{cat}.json").read_text(encoding="utf-8"))
    done, old_ans = {}, {}
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        old_ans = {r["id"]: r["glm_answer"] for r in prev if r.get("glm_answer")}
        # sentiment answers stay valid; factual/summary verdicts are re-judged (new rubric / new gold)
        done = {r["id"]: r for r in prev if r.get("agree") is not None and r["category"] == "sentiment"}
    by_id = {i["id"]: i for i in items}
    for k, r in list(done.items()):  # an item whose text changed must be re-asked
        if by_id[k]["gold"].get("text") not in (None, r.get("text", by_id[k]["gold"].get("text"))):
            del done[k]
    todo = [i for i in items if i["id"] not in done]
    print(f"{len(todo)} items to check ({len(done)} cached)")
    res = await asyncio.gather(*[check_item(p, sem, i, old_ans) for i in todo])
    allrec = list(done.values()) + list(res)
    OUT.write_text(json.dumps(allrec, indent=1, ensure_ascii=False), encoding="utf-8")
    await p.close()
    for cat in ("sentiment", "factual", "summarisation"):
        rs = [r for r in allrec if r["category"] == cat]
        ag = sum(1 for r in rs if r["agree"] is True)
        print(cat, f"agree {ag}/{len(rs)}", "unparsed", sum(1 for r in rs if r["agree"] is None))


if __name__ == "__main__":
    asyncio.run(main())
