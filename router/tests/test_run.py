"""Phase 5 step 3: batch CLI (fake models, no network)."""
import json
import threading
import time

import pytest

from router.config import RouterConfig
from router.fakes import FakeClient
from router.pipeline import Router
from router.policy import Policy, cell_key, placeholder_policy
from router.run import LaneClient, main, run_batch
from router.logging import RequestLogger

PASSING = {"sentiment": "Fine.\nANSWER: positive"}


def make(handler, api_cells=()):
    return Router(Policy(placeholder_policy(api_cells=set(api_cells))), FakeClient(handler), None, RouterConfig())


def sent(i):
    return {"id": f"s{i}", "prompt": f"What is the sentiment of: review number {i}"}


LABELS = lambda ids, d="easy": {i: ["sentiment", d] for i in ids}


def test_batch_writes_all_rows_and_log(tmp_path):
    r = make(lambda m, s, u, mt, jm: PASSING["sentiment"])
    tasks = [sent(i) for i in range(5)]
    out = run_batch(tasks, r, tmp_path / "res.json", RequestLogger(tmp_path / "run.jsonl"), LABELS([t["id"] for t in tasks]), progress=False)
    assert out["meta"]["complete"] and out["meta"]["finished"] == 5
    assert [x["id"] for x in out["results"]] == [t["id"] for t in tasks]
    assert all(x["layer"] == "local" and "prompt" not in x for x in out["results"])
    lines = [json.loads(x) for x in (tmp_path / "run.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 5 and {x["task_id"] for x in lines} == {t["id"] for t in tasks}
    assert "prompt" not in lines[0] and lines[0]["prompt_chars"] > 0 and lines[0]["trace"]


def test_results_written_after_every_task(tmp_path):
    path = tmp_path / "res.json"
    seen = []

    def h(model, system, user, mt, jm):
        if path.exists():   # at the time of task k the file already holds the k-1 earlier results
            seen.append(json.loads(path.read_text(encoding="utf-8"))["meta"]["finished"])
        return PASSING["sentiment"]
    r = make(h)
    tasks = [sent(i) for i in range(4)]
    run_batch(tasks, r, path, None, LABELS([t["id"] for t in tasks]), api_workers=1, progress=False)
    assert seen == [0, 1, 2, 3]


def test_local_calls_sequential_api_calls_parallel(tmp_path):
    active = {"local": 0, "api": 0}
    peak = {"local": 0, "api": 0}
    lock = threading.Lock()

    def h(model, system, user, mt, jm):
        kind = "local" if ":" in model else "api"
        with lock:
            active[kind] += 1
            peak[kind] = max(peak[kind], active[kind])
        time.sleep(0.05)
        with lock:
            active[kind] -= 1
        return PASSING["sentiment"]
    pol = placeholder_policy(api_cells={cell_key("sentiment", "hard")})
    r = Router(Policy(pol), FakeClient(h), None, RouterConfig())
    tasks = [sent(i) for i in range(8)] + [{"id": f"h{i}", "prompt": f"sentiment hard {i}"} for i in range(8)]
    labels = {**LABELS([f"s{i}" for i in range(8)]), **LABELS([f"h{i}" for i in range(8)], "hard")}
    out = run_batch(tasks, r, tmp_path / "r.json", None, labels, api_workers=6, progress=False)
    assert out["meta"]["finished"] == 16
    assert peak["local"] == 1 and peak["api"] >= 2


def test_deadline_skips_unstarted_tasks_and_output_stays_valid(tmp_path):
    now = [0.0]

    def clock():
        return now[0]

    def h(model, system, user, mt, jm):
        now[0] += 10.0                       # each call "takes" 10 s of the fake clock
        return PASSING["sentiment"]
    r = make(h)
    tasks = [sent(i) for i in range(6)]
    out = run_batch(tasks, r, tmp_path / "r.json", None, LABELS([t["id"] for t in tasks]), api_workers=1, deadline_s=25, clock=clock, progress=False)
    status = [x["status"] for x in out["results"]]
    assert status == ["done"] * 3 + ["skipped_deadline"] * 3 and len(out["results"]) == 6
    assert out["results"][-1]["answer"] == ""
    json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))      # valid JSON on disk


def test_lane_client_clamps_timeout_and_refuses_after_deadline():
    fake = FakeClient(lambda *a: "ok")
    now = [0.0]
    lc = LaneClient(fake, deadline=100.0, clock=lambda: now[0])
    lc.chat("glm-5p3", "s", "u", 10, timeout=120)
    assert fake.calls[-1]["timeout"] == pytest.approx(100.0)
    now[0] = 100.0
    r = lc.chat("glm-5p3", "s", "u", 10, timeout=120)
    assert not r.ok and "deadline" in r.error and len(fake.calls) == 1
    assert not lc.chat("gemma3:4b", "s", "u", 10, timeout=30).ok


def test_resume_skips_finished_tasks(tmp_path):
    path = tmp_path / "r.json"
    r1 = make(lambda *a: PASSING["sentiment"])
    tasks = [sent(i) for i in range(4)]
    labels = LABELS([t["id"] for t in tasks])
    run_batch(tasks[:2], r1, path, None, labels, progress=False)
    r2 = make(lambda *a: PASSING["sentiment"])
    out = run_batch(tasks, r2, path, None, labels, resume=True, progress=False)
    assert len(r2.client.calls) == 2 and out["meta"]["finished"] == 4 and out["meta"]["complete"]


def test_duplicate_ids_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_batch([sent(1), sent(1)], make(lambda *a: "x"), tmp_path / "r.json", progress=False)


def test_one_task_failing_does_not_stop_the_batch(tmp_path):
    def h(model, system, user, mt, jm):
        if "number 1" in user:
            return RuntimeError("boom")
        return PASSING["sentiment"]
    r = make(h)
    tasks = [sent(i) for i in range(3)]
    out = run_batch(tasks, r, tmp_path / "r.json", None, LABELS([t["id"] for t in tasks]), progress=False)
    layers = {x["id"]: x["layer"] for x in out["results"]}
    assert layers["s0"] == "local" and layers["s2"] == "local" and layers["s1"] in ("error", "api")


def test_cli_dry_run_prints_plans(tmp_path, capsys):
    tp = tmp_path / "t.json"
    tp.write_text(json.dumps([{"id": "a", "prompt": "anything"}]), encoding="utf-8")
    lp = tmp_path / "l.json"
    lp.write_text(json.dumps({"a": ["factual", "easy"]}), encoding="utf-8")
    pp = tmp_path / "p.json"
    pp.write_text(json.dumps(placeholder_policy()), encoding="utf-8")
    assert main([str(tp), str(tmp_path / "r.json"), "--dry-run", "--labels", str(lp), "--policy", str(pp)]) == 0
    assert "a factual easy local:gemma3:4b -> api:kimi-k3p1-pro" in capsys.readouterr().out
