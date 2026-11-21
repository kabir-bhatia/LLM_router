"""eval_translators on a tiny synthetic translations file built from DEV set-A items (known good translations)."""
import json

from eval.phase4 import eval_translators as et
from router.data import load_dev


def test_pipeline_on_synthetic_replies(tmp_path, monkeypatch):
    dev = {t["id"]: t for t in load_dev()}
    rows = [
        # math-005: 1900 stock, 25% then 10 units -> 1415
        {"task_id": "math-005", "model": "m1", "category": "math", "raw_text": "EXPR: 1900 * (1 - 0.25) - 10", "error": None},
        {"task_id": "math-015", "model": "m1", "category": "math", "raw_text": "EXPR: 1680 * 0.5 - 40 + 1", "error": None},   # stray literal -> defer
        {"task_id": "math-028", "model": "m1", "category": "math", "raw_text": "", "error": "timeout"},
    ]
    p = tmp_path / "translations.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    monkeypatch.setattr(et, "OUT", tmp_path)
    et.main(str(p))
    res = json.loads((tmp_path / "translator_results.json").read_text(encoding="utf-8"))
    s = res["results"]["math"]["all dev"]["m1"]
    assert s["answered"] == 1 and s["correct"] == 1
    comb = json.loads((tmp_path / "solver_cascade_results.json").read_text(encoding="utf-8"))
    assert comb["math-005"]["answered"] and comb["math-005"]["source"] == "pure_python"   # pure-Python answers first
    assert (tmp_path / "translator_report.md").exists()
