"""Phase 5 step 1: config, model client (no network: httpx is faked), policy loading / planning."""
import json

import httpx
import pytest

from router import models as M
from router.config import RouterConfig
from router.models import LiveClient, Prices, kind_of
from router.policy import CATEGORIES, Policy, PolicyError, cell_key, placeholder_policy


# ------------------------------------------------------------------ config
def test_config_defaults_and_env(monkeypatch):
    monkeypatch.setenv("ROUTER_LOCAL_BUDGET_S", "12")
    monkeypatch.setenv("ROUTER_POLICY_PATH", "x/policy.json")
    cfg = RouterConfig()
    assert cfg.local_budget_s == 12 and cfg.policy_path.as_posix().endswith("x/policy.json")
    assert cfg.reasoning_effort == "low" and cfg.semantic_cache is False
    assert cfg.translators == {"math": "phi3.5:3.8b", "logic": "gemma3:4b"}


def test_config_repr_hides_keys(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "sk-secret-123")
    cfg = RouterConfig()
    assert cfg.fireworks_key == "sk-secret-123"
    assert "secret" not in repr(cfg)


# ------------------------------------------------------------------ prices / cost
def test_prices_cost_math():
    p = Prices(RouterConfig().prices_path)
    assert p.per_million("kimi-k3p1-pro") == (2.00, 10.00)
    assert p.cost("kimi-k3p1-pro", 1000, 500) == pytest.approx((1000 * 2 + 500 * 10) / 1e6)
    assert p.cost("gemma3:4b", 10 ** 6, 10 ** 6) == 0.0          # local = $0 marginal
    assert p.cost("hyde/glm-5.3-flash", 1_000_000, 0) == pytest.approx(0.15)
    with pytest.raises(KeyError):
        p.cost("not-a-model", 1, 1)


def test_every_api_model_has_a_price():
    p = Prices(RouterConfig().prices_path)
    for name in M.API_MODELS:
        p.per_million(name)


def test_kind_of():
    assert kind_of("gemma3:4b") == "local" and kind_of("glm-5p3") == "api"


# ------------------------------------------------------------------ client (httpx faked)
class FakeResp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body or {}, text

    def json(self):
        return self._body


def _oa_body(text="ok", tin=100, tout=50, reasoning=20):
    return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": tin, "completion_tokens": tout, "completion_tokens_details": {"reasoning_tokens": reasoning}}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "k")
    monkeypatch.setenv("HYDE_API_KEY", "k")
    monkeypatch.setenv("HYDE_BASE_URL", "http://hyde.test/v1")
    sleeps = []
    c = LiveClient(RouterConfig(), sleep=sleeps.append)
    c.sleeps = sleeps
    return c


def test_openai_success_logs_tokens_and_cost(client, monkeypatch):
    seen = {}

    def post(url, json=None, timeout=None, headers=None):
        seen.update(url=url, payload=json)
        return FakeResp(200, _oa_body())
    monkeypatch.setattr(httpx, "post", post)
    r = client.chat("glm-5p3", "sys", "hi", 100)
    assert r.ok and r.tokens_in == 100 and r.tokens_out == 50 and r.tokens_reasoning == 20
    assert r.cost_usd == pytest.approx((100 * 1.40 + 50 * 4.40) / 1e6)
    assert seen["payload"]["reasoning_effort"] == "low" and seen["payload"]["temperature"] == 0
    assert seen["payload"]["model"].endswith("glm-5p3") and seen["url"].endswith("/chat/completions")


def test_retries_on_429_then_succeeds(client, monkeypatch):
    calls = []

    def post(url, **kw):
        calls.append(1)
        return FakeResp(429, text="slow down") if len(calls) < 3 else FakeResp(200, _oa_body())
    monkeypatch.setattr(httpx, "post", post)
    r = client.chat("gpt-oss-120b", "s", "u", 50)
    assert r.ok and r.attempts == 3 and len(calls) == 3 and client.sleeps == [20.0, 30.0]  # backoff capped at 30 s


def test_no_retry_on_400_and_never_raises(client, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp(400, text="bad request"))
    r = client.chat("gpt-oss-120b", "s", "u", 50)
    assert not r.ok and "HTTP 400" in r.error and r.attempts == 1 and r.cost_usd == 0.0


def test_gives_up_after_retries(client, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp(503, text="down"))
    r = client.chat("gpt-oss-120b", "s", "u", 50)
    assert not r.ok and "503" in r.error and r.attempts == client.cfg.api_retries


def test_transport_error_is_retried(client, monkeypatch):
    n = []

    def post(*a, **k):
        n.append(1)
        if len(n) == 1:
            raise httpx.ConnectError("boom")
        return FakeResp(200, _oa_body())
    monkeypatch.setattr(httpx, "post", post)
    assert client.chat("hyde/glm-5.3-flash", "s", "u", 50).ok


def test_missing_key_fails_fast_without_network(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "")
    monkeypatch.setattr("router.config._secret", lambda *a: "")
    c = LiveClient(RouterConfig(), sleep=lambda s: None)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("network used"))
    r = c.chat("glm-5p3", "s", "u", 10)
    assert not r.ok and "not configured" in r.error


def test_blank_reply_is_not_ok(client, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp(200, _oa_body(text="  ")))
    r = client.chat("glm-5p3", "s", "u", 10)
    assert r.error is None and not r.ok


def test_ollama_call_options_and_timeout(client, monkeypatch):
    seen = {}

    def post(url, json=None, timeout=None, **k):
        seen.update(url=url, payload=json, timeout=timeout)
        return FakeResp(200, {"message": {"content": "hello"}, "prompt_eval_count": 7, "eval_count": 3, "done_reason": "stop"})
    monkeypatch.setattr(httpx, "post", post)
    r = client.chat("qwen3:1.7b", "s", "u", 256, timeout=9)
    assert r.ok and r.cost_usd == 0.0 and r.tokens_out == 3
    p = seen["payload"]
    assert p["think"] is False and p["options"]["num_predict"] == 256 and p["options"]["num_thread"] == 2
    assert p["options"]["temperature"] == 0 and seen["timeout"] == 9 and seen["url"].endswith("/api/chat")


def test_ollama_timeout_becomes_error(client, monkeypatch):
    def post(*a, **k):
        raise httpx.ReadTimeout("slow")
    monkeypatch.setattr(httpx, "post", post)
    r = client.chat("gemma3:4b", "s", "u", 10, timeout=5)
    assert not r.ok and "timeout" in r.error


def test_unknown_api_model(client):
    r = client.chat("mystery-model", "s", "u", 10)
    assert not r.ok and "unknown model" in r.error


# ------------------------------------------------------------------ policy
def test_real_policy_loads_and_validates():
    cfg = RouterConfig()
    if not cfg.policy_path.exists():
        pytest.skip("no policy file")
    pol = Policy.load(cfg.policy_path)
    assert pol.b1 and len(pol.data["cells"]) == 16


def test_placeholder_policy_is_valid_and_full():
    pol = Policy(placeholder_policy())
    assert all(pol.cell(c, d) for c in CATEGORIES for d in ("easy", "hard"))
    assert "gemma3:4b" in pol.models() and "kimi-k3p1-pro" in pol.models()


def test_plan_local_cell_math_has_solver_then_local_then_b1():
    pol = Policy(placeholder_policy())
    plan = pol.plan("math", "hard")
    assert [(s.kind, s.model) for s in plan.steps] == [("solver", ""), ("local", "gemma3:4b"), ("api", "kimi-k3p1-pro")]
    assert [s.kind for s in pol.plan("factual", "easy").steps] == ["local", "api"]   # no solver outside math/logic


def test_plan_api_cell_retries_one_tier_up():
    pol = Policy(placeholder_policy(api_cells={cell_key("ner", "hard")}))
    assert [(s.kind, s.model, s.role) for s in pol.plan("ner", "hard").steps] == [
        ("api", "deepseek-v4p1-flash", "primary"), ("api", "kimi-k3p1-pro", "retry")]


def test_plan_b1_cell_has_single_step():
    d = placeholder_policy(mid="kimi-k3p1-pro", api_cells={cell_key("ner", "hard")})
    assert len(Policy(d).plan("ner", "hard").steps) == 1


def test_plan_out_of_scope_goes_to_b1():
    plan = Policy(placeholder_policy()).plan("out_of_scope", "easy")
    assert plan.cell == "out_of_scope" and [(s.kind, s.model) for s in plan.steps] == [("api", "kimi-k3p1-pro")]


def test_plan_respects_solvers_disabled():
    d = placeholder_policy()
    d["solvers_enabled"] = False
    assert [s.kind for s in Policy(d).plan("logic", "easy").steps] == ["local", "api"]
    assert [s.kind for s in Policy(placeholder_policy()).plan("logic", "easy", use_solvers=False).steps] == ["local", "api"]


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d.pop("b1"), "missing key"),
    (lambda d: d.update(b1="gemma3:4b"), "b1"),
    (lambda d: d.update(b1="no-such-api-model"), "b1"),
    (lambda d: d["cells"].pop("math|easy"), "missing cells"),
    (lambda d: d["cells"]["math|easy"].update(model="mystery"), "unknown model"),
    (lambda d: d["cells"]["math|easy"].update(kind="api"), "does not match"),
    (lambda d: d["cells"]["math|easy"].update(escalate_to="gemma3:4b"), "escalate_to"),
    (lambda d: d["cells"].update({"bogus|easy": {"model": "gemma3:4b"}}), "bad cell key"),
    (lambda d: d["out_of_scope"].update(model="gemma3:4b"), "out_of_scope"),
])
def test_validation_rejects_bad_policies(mutate, msg):
    d = placeholder_policy()
    mutate(d)
    with pytest.raises(PolicyError, match=msg):
        Policy(d)


def test_partial_policy_allowed_when_requested_and_missing_cell_goes_to_b1():
    d = placeholder_policy()
    del d["cells"]["math|easy"]
    pol = Policy(d, require_full_grid=False)
    assert [(s.kind, s.model) for s in pol.plan("math", "easy").steps] == [("api", "kimi-k3p1-pro")]


def test_load_errors(tmp_path):
    with pytest.raises(PolicyError, match="cannot read"):
        Policy.load(tmp_path / "nope.json")
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(PolicyError):
        Policy.load(f)
    g = tmp_path / "p.json"
    g.write_text(json.dumps(placeholder_policy()), encoding="utf-8")
    assert Policy.load(g).b1 == "kimi-k3p1-pro"
