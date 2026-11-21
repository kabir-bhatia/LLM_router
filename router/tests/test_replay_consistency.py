"""Phase 5 step 5, the most important test: the production Router, fed the recorded Phase 3/4 answers, reproduces policy_lib.replay()
over all 240 dev tasks, with the true labels and with the classifiers' predicted labels (eval/results/phase4/predicted_labels.json).
Reads the policy from RouterConfig (ROUTER_POLICY_PATH), so it follows whatever policy Phase 4 last wrote. Dev split only."""
import pytest

from router.config import RouterConfig
from router.replay_check import load_inputs, run_check

pytestmark = pytest.mark.skipif(not RouterConfig().policy_path.exists(), reason="no routing policy file")


@pytest.fixture(scope="module")
def inputs():
    try:
        return load_inputs()
    except FileNotFoundError as e:
        pytest.skip(f"Phase 3/4 data missing: {e}")


@pytest.fixture(scope="module")
def checks(inputs):
    return {name: run_check(name, inputs=inputs) for name in ("true", "predicted")}


def test_true_labels_match_official_replay_exactly(checks):
    r = checks["true"]
    ref = r["replay_official"]
    assert r["n"] == 240
    assert ref["unexplained_mismatches"] == [] and ref["label_validator_tasks"] == []
    assert r["router"]["accuracy"] == pytest.approx(ref["accuracy"], abs=1e-12)
    assert r["router"]["cost_usd"] == pytest.approx(ref["cost_usd"], abs=1e-9)
    assert r["router"]["paths"] == {**ref["paths"], "error": 0}


def test_predicted_labels_match_replay_with_predicted_category_exactly(checks):
    r = checks["predicted"]
    ref = r["replay_predicted_category"]
    assert ref["unexplained_mismatches"] == []
    assert r["router"]["accuracy"] == pytest.approx(ref["accuracy"], abs=1e-12)
    assert r["router"]["cost_usd"] == pytest.approx(ref["cost_usd"], abs=1e-9)
    assert r["router"]["paths"] == {**ref["paths"], "error": 0}


def test_predicted_labels_vs_official_replay_only_label_validator_differences(checks, inputs):
    ref = checks["predicted"]["replay_official"]
    assert ref["unexplained_mismatches"] == []
    true_cat = {t["id"]: t["category"] for t in inputs[1]}
    for d in ref["label_validator_tasks"]:        # reported, never hidden: category misclassified, so the validator differs
        assert d["router"]["category"] != true_cat[d["id"]]
    print("label-validator tasks:", [d["id"] for d in ref["label_validator_tasks"]])


def test_blank_api_retry_divergences_are_reported_separately(checks):
    # the replay does not model "blank API reply -> one retry up"; on the current dev policy no routed model gave a blank answer
    for name, r in checks.items():
        for ref in [k for k in r if k.startswith("replay_")]:
            blanks = r[ref]["blank_api_retry_tasks"]
            assert isinstance(blanks, list)
            for d in blanks:
                assert d["router"]["escalated"]
    print({n: {k: len(v["blank_api_retry_tasks"]) for k, v in r.items() if k.startswith("replay_")} for n, r in checks.items()})


def test_headline_numbers_follow_the_policy_guardrail(checks, inputs):
    import json
    pol = json.loads(inputs[0].policy_path.read_text(encoding="utf-8"))
    fin = pol.get("guardrail", {}).get("final")
    if not fin:
        pytest.skip("policy has no guardrail summary")
    # the guardrail was computed on predicted labels with the official replay
    assert checks["predicted"]["replay_official"]["accuracy"] == pytest.approx(fin["router_accuracy"], abs=1e-9)
    assert checks["predicted"]["replay_official"]["cost_usd"] == pytest.approx(fin["router_cost_usd"], abs=1e-9)


def test_no_errors_and_no_call_outside_the_policy(checks):
    for r in checks.values():
        assert r["router"]["paths"]["error"] == 0


def test_injected_blank_api_reply_is_detected_and_reported_separately(inputs):
    """Blank the recorded first-choice API answer of one ner|easy task: the router retries on B2, the replay cannot, and the check
    files it under blank_api_retry (not 'unexplained')."""
    tid = next(t["id"] for t in inputs[1] if t["category"] == "ner" and t["difficulty"] == "easy")
    cell = __import__("router.policy", fromlist=["Policy"]).Policy.load(inputs[0].policy_path).cell("ner", "easy")
    if cell["kind"] != "api" or cell["model"] == cell["escalate_to"]:
        pytest.skip("ner|easy is not an API cell with a distinct retry tier in this policy")

    def blank(client):
        client.api_rows[(cell["model"], tid)] = {**client.api_rows[(cell["model"], tid)], "raw_text": ""}
    r = run_check("true", inputs=inputs, client_hook=blank)
    ref = r["replay_official"]
    assert [d["id"] for d in ref["blank_api_retry_tasks"]] == [tid] and ref["unexplained_mismatches"] == []
    assert ref["blank_api_retry_tasks"][0]["router"]["trace"][-1][1] == cell["escalate_to"]
