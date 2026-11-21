"""Run the zero-shot GLM classifier (free Hyde endpoint) on the 240 dev prompts + 30 OOS prompts; cache to disk."""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from router.classify import llm_classify
from router.data import ROOT, load_dev

OUT = ROOT / "eval" / "results" / "phase4" / "llm_classifier_raw.jsonl"


def key(p):
    return hashlib.sha1(p.encode("utf-8")).hexdigest()


def main():
    dev = load_dev()
    oos = json.loads((ROOT / "eval" / "phase4" / "oos_prompts.json").read_text(encoding="utf-8"))["prompts"]
    items = [(t["prompt"], t["category"]) for t in dev] + [(p, "out_of_scope") for p in oos]
    done = {}
    if OUT.exists():
        for ln in OUT.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                done[r["key"]] = r
    todo = [(p, c) for p, c in items if key(p) not in done and not done.get(key(p), {}).get("raw", "").startswith("FAILED")]
    print(f"{len(done)} cached, {len(todo)} to run", flush=True)

    def work(it):
        p, c = it
        r = llm_classify(p)
        r.update({"key": key(p), "true": c})
        return r

    with ThreadPoolExecutor(6) as ex, open(OUT, "a", encoding="utf-8") as f:
        for i, r in enumerate(ex.map(work, todo), 1):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if i % 30 == 0:
                print(i, flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
