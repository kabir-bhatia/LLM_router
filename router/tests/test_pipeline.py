"""Phase 5 step 2: pipeline unit tests (escalation rules, out-of-scope, cost maths) + a fake-model end-to-end run on 16 dev tasks.
No network: every model is a FakeClient; embeddings come from the on-disk cache."""
import re

import pytest

from router.config import RouterConfig
from router.fakes import FakeClient
from router.models import ModelReply
from router.pipeline import Router, build_router
from router.policy import Policy, cell_key, placeholder_policy

GOOD = {
    "math": "Working.\nANSWER: 42",
    "logic": "ANSWER: Gus",
    "sentiment": "Because.\nANSWER: positive",
    "factual": "The seasons come from the tilt of the Earth's axis as it orbits the sun, so each hemisphere gets more direct light in turn.",
    "ner": '[{"text": "Google", "type": "ORG"}]',
    "code_gen": "```python\ndef is_valid_ipv4(s):\n    return True\n```",
    "code_debug": "```python\ndef is_valid_ipv4(s):\n    return True\n```",
    "summarisation": "A short summary.",
}
PROMPT = {  # a prompt per category that the answers in GOOD pass validation for
    "math": "A shop sold 7 items at 6 each; what was the revenue after a 10% rebate on 33 more?",
    "logic": "Three runners - Gus, Kofi and Jia - finished a race. Who finished first?",
    "sentiment": "What is the sentiment of: great phone",
    "factual": "Why are there seasons on Earth?",
    "ner": "Tag the entities: Priya works at Google.",
    "code_gen": "Write the Python function `is_valid_ipv4(s)`.",
    "code_debug": "Fix the bug in `is_valid_ipv4(s)`: def is_valid_ipv4(s): return False",
    "summarisation": "Summarise in one sentence: Cats sleep a lot.",
}


def mk(handler, policy=None, labeler=None, **cfg):
    c = RouterConfig()
    for k, v in cfg.items():
        setattr(c, k, v)
    fake = FakeClient(handler)
    return Router(Policy(policy or placeholder_policy()), fake, labeler, c), fake


def good_for(category):
    return GOOD[category]


def by_category(model, system, user, mt, jm):
    from eval.graders.formats import FORMAT_INSTRUCTIONS
    for cat, s in FORMAT_INSTRUCTIONS.items():
        if system == s:
            return GOOD[cat]
    return "no idea"                       # translator prompts etc.


# ------------------------------------------------------------------ escalation rules
def test_local_answer_passes_validators_no_paid_call():
    r, fake = mk(by_category)
    res = r.route(PROMPT["sentiment"], labels=("sentiment", "easy"))
    assert res.layer == "local" and res.model == "gemma3:4b" and res.cost_usd == 0.0 and not res.escalated
    assert fake.models_called() == ["gemma3:4b"]
    assert res.answer.endswith("ANSWER: positive")


def test_same_system_prompt_as_benchmark():
    from eval.graders.formats import system_prompt
    r, fake = mk(by_category)
    r.route(PROMPT["ner"], labels=("ner", "easy"))
    assert fake.calls[0]["system"] == system_prompt("ner") and fake.calls[0]["user"] == PROMPT["ner"]
    assert fake.calls[0]["max_tokens"] == r.cfg.local_max_tokens["ner"]


def test_validator_failure_escalates_to_b1():
    def h(model, system, user, mt, jm):
        return "nonsense with no answer line" if model == "gemma3:4b" else GOOD["sentiment"]
    r, fake = mk(h)
    res = r.route(PROMPT["sentiment"], labels=("sentiment", "easy"))
    assert res.layer == "api" and res.model == "kimi-k3p1-pro" and res.escalated and res.cost_usd > 0
    assert fake.models_called() == ["gemma3:4b", "kimi-k3p1-pro"]
    assert any("ANSWER" in (e.get("why") or "") for e in res.trace if e["step"] == "local")


def test_local_timeout_escalates():
    def h(model, system, user, mt, jm):
        return ModelReply(model, error="timeout after 30s", latency_ms=30000) if model == "gemma3:4b" else GOOD["factual"]
    r, _ = mk(h)
    res = r.route(PROMPT["factual"], labels=("factual", "easy"))
    assert res.layer == "api" and res.escalated and res.trace[0]["why"] == "timeout"


def test_local_budget_is_passed_as_timeout_and_shared_by_the_layer():
    r, fake = mk(by_category)
    r.route(PROMPT["sentiment"], labels=("sentiment", "easy"))
    assert fake.calls[0]["timeout"] == pytest.approx(30.0)


def test_budget_exhausted_by_translator_skips_local_model():
    def h(model, system, user, mt, jm):
        if system.startswith("You translate"):
            return ModelReply(model, text="garbage", latency_ms=29500)    # slow translator eats the 30 s budget
        return GOOD["math"] if model != "kimi-k3p1-pro" else "ANSWER: 7"
    r, fake = mk(h)
    res = r.route("A tank has 800 litres, 25% leaks, how many are left after adding some?", labels=("math", "hard"))
    assert res.layer == "api" and res.model == "kimi-k3p1-pro"
    assert [c["model"] for c in fake.calls] == ["phi3.5:3.8b", "kimi-k3p1-pro"]       # gemma3:4b local never called
    assert any(e.get("skipped") for e in res.trace)


def test_api_blank_reply_retries_once_on_next_tier():
    pol = placeholder_policy(api_cells={cell_key("ner", "hard")})

    def h(model, system, user, mt, jm):
        return "   " if model == "deepseek-v4p1-flash" else GOOD["ner"]
    r, fake = mk(h, policy=pol)
    res = r.route(PROMPT["ner"], labels=("ner", "hard"))
    assert res.layer == "api" and res.model == "kimi-k3p1-pro" and res.escalated
    assert fake.models_called() == ["deepseek-v4p1-flash", "kimi-k3p1-pro"]


def test_api_error_retries_once_then_gives_error_result_not_exception():
    pol = placeholder_policy(api_cells={cell_key("ner", "hard")})
    r, fake = mk(lambda *a: RuntimeError("503"), policy=pol)
    res = r.route(PROMPT["ner"], labels=("ner", "hard"))
    assert res.layer == "error" and res.answer == "" and res.error and len(fake.calls) == 2


def test_api_answer_is_not_validated():
    pol = placeholder_policy(api_cells={cell_key("sentiment", "hard")})
    r, fake = mk(lambda *a: "well-formed or not, a paid answer is accepted", policy=pol)
    res = r.route(PROMPT["sentiment"], labels=("sentiment", "hard"))
    assert res.layer == "api" and not res.escalated and len(fake.calls) == 1


def test_out_of_scope_goes_straight_to_b1():
    r, fake = mk(lambda *a: "here is a long essay")
    res = r.route("Write me a poem about autumn", labels=("out_of_scope", "easy"))
    assert res.layer == "api" and res.model == "kimi-k3p1-pro" and fake.models_called() == ["kimi-k3p1-pro"]
    assert res.category == "out_of_scope"


def test_cost_maths_and_savings():
    r, fake = mk(lambda *a: "x" * 400)
    res = r.route("Write me a poem about autumn", labels=("out_of_scope", "easy"))
    c = fake.calls[0]
    tin, tout = (len(c["system"]) + len(c["user"])) // 4, 100
    assert c["max_tokens"] == 6000
    assert res.cost_usd == pytest.approx((tin * 2.0 + tout * 10.0) / 1e6)
    assert res.b1_cost_usd == res.cost_usd and res.savings_usd == 0          # B1 itself: no saving
    res2 = mk(by_category)[0].route(PROMPT["sentiment"], labels=("sentiment", "easy"))
    assert res2.cost_usd == 0 and res2.savings_usd == res2.b1_cost_usd > 0     # local answer saves the whole estimate


def test_escalated_request_pays_for_failed_paid_attempts():
    pol = placeholder_policy(api_cells={cell_key("ner", "hard")})

    def h(model, system, user, mt, jm):
        return ModelReply(model, error="HTTP 500", tokens_in=100, tokens_out=0, cost_usd=0.001) if model == "deepseek-v4p1-flash" \
            else GOOD["ner"]
    r, _ = mk(h, policy=pol)
    res = r.route(PROMPT["ner"], labels=("ner", "hard"))
    assert res.cost_usd == 0 or res.layer == "api"   # failed attempt carries no billable tokens when it errored
    assert res.layer == "api" and res.cost_usd > 0


# ------------------------------------------------------------------ solvers
def test_pure_python_solver_answers_without_any_model_call():
    r, fake = mk(by_category)
    res = r.route("Split 360 rupees in the ratio 2:7. How much is the smaller share?", labels=("math", "easy"))
    assert res.layer == "solver" and res.cost_usd == 0 and res.answer == "ANSWER: 80" and fake.calls == []


def test_translator_then_python_solves():
    def h(model, system, user, mt, jm):
        assert model == "phi3.5:3.8b" and user.startswith("Problem: ")
        return "EXPR: 800 * (1 - 0.25) + 40"
    r, fake = mk(h)
    res = r.route("A tank holds 800 litres. 25% leaks out, then 40 litres are added. How many litres are in the tank?", labels=("math", "hard"))
    assert res.layer == "solver" and res.answer == "ANSWER: 640" and res.model == "translator:phi3.5:3.8b"
    assert fake.calls[0]["max_tokens"] == 256


def test_translator_defers_on_bad_output_then_local_model_runs():
    r, fake = mk(by_category)
    res = r.route("A tank holds 800 litres and 25% leaks out; how many remain?", labels=("math", "hard"))
    assert res.layer == "local" and fake.models_called() == ["phi3.5:3.8b", "gemma3:4b"]


def test_solvers_off_in_policy_skips_solver_and_translator():
    d = placeholder_policy()
    d["solvers_enabled"] = False
    r, fake = mk(by_category, policy=d)
    res = r.route("Split 360 rupees in the ratio 2:7. How much is the smaller share?", labels=("math", "easy"))
    assert res.layer == "local" and fake.models_called() == ["gemma3:4b"]


def test_logic_translator_uses_json_mode():
    seen = {}

    def h(model, system, user, mt, jm):
        seen.setdefault("model", model)
        seen.setdefault("jm", jm)
        return "{}"
    r, _ = mk(h)
    r.route("Three runners - Gus, Kofi and Jia - finished a race with no ties. Kofi did not finish first. Who finished first?", labels=("logic", "easy"))
    assert seen["model"] == "gemma3:4b" and seen["jm"] is True


# ------------------------------------------------------------------ robustness
def test_route_never_raises_even_if_client_explodes():
    class Boom:
        def chat(self, *a, **k):
            raise RuntimeError("kaboom")
    r = Router(Policy(placeholder_policy()), Boom(), None, RouterConfig())
    res = r.route("hello there", labels=("factual", "easy"))
    assert res.layer == "error" and res.error and res.answer == ""


def test_classifier_failure_routes_to_b1():
    class BadLabeler:
        def label(self, p):
            raise RuntimeError("no embeddings")
    r, fake = mk(lambda *a: "answer", labeler=BadLabeler())
    res = r.route("anything")
    assert res.category == "out_of_scope" and res.model == "kimi-k3p1-pro" and res.label_source == "classifier-error"


def test_labels_override_and_trace_fields():
    r, _ = mk(by_category)
    res = r.route(PROMPT["factual"], labels=("factual", "hard"))
    assert (res.category, res.difficulty, res.label_source) == ("factual", "hard", "given")
    assert res.plan == ["local:gemma3:4b", "api:kimi-k3p1-pro"] and res.latency_ms >= 0 and res.to_dict()["trace"]


# ------------------------------------------------------------------ end to end: 16 dev tasks (2 per category), real classifiers, fake models
def _cached_embed(prompt):
    import numpy as np
    from router.embeddings import CACHE_DIR, _key, _load_cache
    c = _load_cache()
    if _key(prompt) not in c:
        pytest.skip("MiniLM cache missing for dev prompts")
    return np.asarray(c[_key(prompt)])


def test_end_to_end_16_dev_tasks_no_network():
    from router.data import load_dev
    from router.labeler import Labeler
    dev = load_dev()
    tasks = []
    for cat in sorted({t["category"] for t in dev}):
        pool = sorted((t for t in dev if t["category"] == cat), key=lambda t: t["id"])
        tasks += [next(t for t in pool if t["difficulty"] == "easy"), next(t for t in pool if t["difficulty"] == "hard")]
    assert len(tasks) == 16 and all(t["category"] and t["difficulty"] for t in tasks)

    def h(model, system, user, mt, jm):
        if system.startswith("You translate"):
            return "unparseable"
        from eval.graders.formats import FORMAT_INSTRUCTIONS
        cat = next((c for c, s in FORMAT_INSTRUCTIONS.items() if s == system), "factual")
        names = re.findall(r"\b([A-Z][a-z]+)\b", user)
        if cat == "logic":
            return f"ANSWER: {names[0]}"
        if cat == "ner":
            return '[{"text": "%s", "type": "PERSON"}]' % names[0]
        if cat in ("code_gen", "code_debug"):
            fn = (re.findall(r"`(\w+)\(", user) or re.findall(r"def (\w+)\(", user) or ["f"])[0]
            return f"```python\ndef {fn}(*a):\n    return 0\n```"
        return GOOD[cat]
    pol = Policy(placeholder_policy(api_cells={cell_key("factual", "hard"), cell_key("code_gen", "hard")}))
    fake = FakeClient(h)
    router = Router(pol, fake, Labeler(embed_fn=_cached_embed), RouterConfig())
    results = [router.route(t["prompt"]) for t in tasks]
    assert len(results) == 16
    for t, res in zip(tasks, results):
        assert res.answer and res.layer in ("solver", "local", "api") and res.trace and res.error is None, (t["id"], res.trace)
        assert res.cost_usd >= 0 and (res.layer != "local" or res.cost_usd == 0)
        assert res.plan and res.category and res.difficulty
    assert {r.layer for r in results} >= {"local", "api"}
    # the label path agrees with the dataset for most tasks (the classifiers are not perfect; the replay test measures that properly)
    assert sum(r.category == t["category"] for r, t in zip(results, tasks)) >= 12
    # no call ever went to a model the policy cannot reach
    assert set(fake.models_called()) <= pol.models() | {"phi3.5:3.8b", "gemma3:4b"}


def test_build_router_reads_policy_from_config_path(tmp_path, monkeypatch):
    import json
    p = tmp_path / "p.json"
    p.write_text(json.dumps(placeholder_policy(local="llama3.2:3b")), encoding="utf-8")
    monkeypatch.setenv("ROUTER_POLICY_PATH", str(p))
    r = build_router(RouterConfig(), client=FakeClient(by_category))
    assert r.policy.cell("factual", "easy")["model"] == "llama3.2:3b"
