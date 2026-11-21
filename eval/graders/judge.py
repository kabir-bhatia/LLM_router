"""Blind judge (D8). Phase 1 ships only the prompt builder and verdict parser; the model call is Phase 2.

The judge sees the question, the reference answer + key points and ONE candidate answer, with no
model name, and returns PASS or FAIL.
"""

from __future__ import annotations

import re

from .common import GradeResult, strip_thinking

JUDGE_PROMPT = """You are a strict but fair grader. Judge ONE candidate answer against a reference.

Question:
{question}

Reference answer:
{reference}

REQUIRED key points (each must be present, in any wording):
{key_points}

OPTIONAL key points (nice to have; their absence is NOT a reason to fail):
{optional}

Candidate answer:
{answer}

Rules:
- FAIL if the candidate states something that is wrong or contradicts the reference or the source text,
  or if a REQUIRED key point is missing.
- Extra detail that is correct but not in the reference must NOT cause a FAIL. Only fail added content
  if it is actually wrong or contradicts the reference/source.
- Ignore style and length unless the question sets a limit.
- Simplifications that standard popular-science explanations use are fine (for example "greenhouse gases trap the
  sun's heat"). Statements a textbook would call wrong are not (for example "observing a particle disturbs it" as the
  meaning of the uncertainty principle).
Reply with one line: VERDICT: PASS or VERDICT: FAIL, then one short sentence of reason."""

SUMMARY_PROMPT = """You are a strict but fair grader. Judge ONE candidate summary against its source text.

Source text:
{source}

CORE facts (BOTH must be present in the summary, in any wording):
{core}

SECONDARY facts (nice to have; their absence is NEVER a reason to fail):
{secondary}

Candidate summary:
{answer}

Rules:
- PASS only if BOTH core facts are present AND nothing in the summary is wrong.
- FAIL if either core fact is missing. A one-sided summary that leaves out the story's main downside or "but" fails when
  that is a core fact.
- FAIL if the summary contradicts the source, invents a fact or a cause that the source does not state, or reverses a
  relationship (for example saying growers worry about jobs when the source says growers are short of workers).
- Do NOT fail for: missing secondary facts or numbers; dropping a qualifier while keeping the direction of the claim
  (for example "remote workers were less likely to be promoted" for "juniors remote more than four days were");
  wording a non-expert explanation would use; correct detail from the source that is not listed above.
- Ignore style and length (the length/format limit is checked elsewhere).
Reply with one line: VERDICT: PASS or VERDICT: FAIL, then one short sentence of reason."""


def build_summary_prompt(source: str, core: list, secondary: list, answer: str) -> str:
    fmt = lambda xs: "\n".join(f"- {k}" for k in xs) or "- (none)"
    return SUMMARY_PROMPT.format(source=source, core=fmt(core), secondary=fmt(secondary),
                                 answer=strip_thinking(answer).strip())


def build_judge_prompt(question: str, reference: str, key_points: list, answer: str, optional=None) -> str:
    """key_points = REQUIRED points; optional = nice-to-have points (never decide pass/fail)."""
    kp = "\n".join(f"- {k}" for k in key_points) or "- (none)"
    op = "\n".join(f"- {k}" for k in (optional or [])) or "- (none)"
    return JUDGE_PROMPT.format(question=question, reference=reference, key_points=kp, optional=op,
                               answer=strip_thinking(answer).strip())


def parse_verdict(text: str):
    m = re.findall(r"VERDICT\s*:\s*(PASS|FAIL)", strip_thinking(text), re.IGNORECASE)
    return m[-1].upper() == "PASS" if m else None


# ----------------------------------------------------------------------------------------------
# Phase 2: real judge calls (D8). Blind: the prompt never contains a model name. Both judges run at
# low reasoning effort with a capped token budget. Verdicts are cached on disk (judge_cache.jsonl) by
# (judge, prompt) so re-grading saved answers costs nothing. Fireworks spend is tracked in
# eval/results/phase2_spend.json and every call is refused once the --max-cost stop is reached.
# ----------------------------------------------------------------------------------------------

import hashlib
import json
import threading
import time
from pathlib import Path

JUDGES = {
    "glm": {"provider": "hyde", "model": "hyde/glm-5.3-flash", "price": (0.0, 0.0)},  # free to us
    "qwen": {"provider": "fireworks", "model": "accounts/fireworks/models/qwen3p8-max", "price": (2.00, 6.00)},
}
JUDGE_MAX_TOKENS = 1500  # reasoning tokens count against this; verdict line is short
JUDGE_REASONING_EFFORT = "low"
DEFAULT_MAX_COST = 0.50  # USD, hard stop for the whole of Phase 2 (all Fireworks judge calls)

_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = _ROOT / "results" / "judge_cache.jsonl"
SPEND_PATH = _ROOT / "results" / "phase2_spend.json"
_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


def spent_usd() -> float:
    try:
        return float(json.loads(SPEND_PATH.read_text(encoding="utf-8")).get("fireworks_usd", 0.0))
    except (OSError, ValueError):
        return 0.0


def _add_spend(usd: float, tokens_in: int, tokens_out: int) -> None:
    with _lock:
        d = {"fireworks_usd": 0.0, "calls": 0, "tokens_in": 0, "tokens_out": 0}
        try:
            d.update(json.loads(SPEND_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        d["fireworks_usd"] = round(d["fireworks_usd"] + usd, 6)
        d["calls"] += 1
        d["tokens_in"] += tokens_in
        d["tokens_out"] += tokens_out
        SPEND_PATH.write_text(json.dumps(d, indent=1), encoding="utf-8")


def _cache_key(judge: str, prompt: str) -> str:
    return hashlib.sha256((judge + "\n" + prompt).encode("utf-8")).hexdigest()


def _cache_load() -> dict:
    out = {}
    if CACHE_PATH.exists():
        for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["key"]] = r
    return out


def call_judge(judge: str, prompt: str, max_cost: float = DEFAULT_MAX_COST, use_cache: bool = True) -> dict:
    """One blind judge call. Returns {passed: True/False/None, reason, judge, tokens_in, tokens_out, cost_usd, cached}."""
    import httpx

    from src.config import get_settings

    cfg = JUDGES[judge]
    key = _cache_key(judge, prompt)
    if use_cache:
        with _lock:
            hit = _cache_load().get(key)
        if hit:
            return {**hit["result"], "cached": True}
    if cfg["provider"] == "fireworks" and spent_usd() >= max_cost:
        raise BudgetExceeded(f"Fireworks spend {spent_usd():.4f} >= max {max_cost}")
    s = get_settings()
    base, token = ((s.hyde_base_url, s.hyde_api_key) if cfg["provider"] == "hyde"
                   else (s.fireworks_base_url, s.fireworks_api_key))
    payload = {"model": cfg["model"], "temperature": 0.0, "max_tokens": JUDGE_MAX_TOKENS,
               "reasoning_effort": JUDGE_REASONING_EFFORT,
               "messages": [{"role": "user", "content": prompt}]}
    last_err = ""
    for k in range(4):
        try:
            r = httpx.post(base.strip().rstrip("/") + "/chat/completions", json=payload, timeout=180,
                           headers={"Authorization": f"Bearer {token.strip()}"})
            if r.status_code == 429 or r.status_code >= 500:
                last_err = f"HTTP {r.status_code}"
                time.sleep(3 * (k + 1))
                continue
            r.raise_for_status()
            data = r.json()
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            tin, tout = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            cost = (tin * cfg["price"][0] + tout * cfg["price"][1]) / 1e6
            if cfg["provider"] == "fireworks":
                _add_spend(cost, tin, tout)
            verdict = parse_verdict(text)
            if verdict is None and k < 3 and not text.strip():
                last_err = "empty reply"
                time.sleep(2)
                continue
            res = {"passed": verdict, "reason": strip_thinking(text).strip()[:300], "judge": judge,
                   "tokens_in": tin, "tokens_out": tout, "cost_usd": cost, "cached": False}
            if use_cache:
                with _lock:
                    with open(CACHE_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"key": key, "result": res}, ensure_ascii=False) + "\n")
            return res
        except httpx.HTTPError as e:
            last_err = str(e)[:200]
            time.sleep(3 * (k + 1))
    return {"passed": None, "reason": f"judge call failed: {last_err}", "judge": judge,
            "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "cached": False}


def judge_prompt_for_task(task: dict, answer_text: str) -> str:
    """Build the blind judge prompt for a factual or summarisation task (answer_text = raw model output)."""
    g = task["gold"]
    if task["category"] == "factual":
        return build_judge_prompt(g["question"], g["reference"], g["key_points"], answer_text,
                                  optional=g.get("optional_points"))
    from .constraint import summary_text

    return build_summary_prompt(g["source_text"], g["core_facts"], g["secondary_facts"], summary_text(answer_text))


def make_judge_fn(name: str, max_cost: float = DEFAULT_MAX_COST):
    """Return fn(task, answer_record, grade_result) -> {passed, reason, judge} for eval.grade.

    name: "glm", "qwen" or "default". "default" follows the D8 rule: the chosen default judge (set in
    DEFAULT_JUDGE after the Phase 2 calibration) grades everything except answers from a hyde/glm model,
    which qwen grades so no model grades itself.
    """
    if name == "default":
        name = DEFAULT_JUDGE

    def fn(task, ans, res):
        j = name
        if "glm" in ans["model"].lower() and JUDGES[j]["provider"] == "hyde":
            j = "qwen"
        out = call_judge(j, judge_prompt_for_task(task, ans["raw_text"]), max_cost)
        return {"passed": out["passed"], "reason": out["reason"], "judge": j}

    return fn


DEFAULT_JUDGE = "glm"  # D8 rule, round 2 calibration: GLM 92.5% >= 90% and within 5 points of Qwen 87.5% (results/judge_decision.md)


def judge(task: dict, answer_text: str, which: str = "glm", max_cost: float = DEFAULT_MAX_COST) -> GradeResult:
    out = call_judge(which, judge_prompt_for_task(task, answer_text), max_cost)
    return GradeResult(out["passed"], 1.0 if out["passed"] else 0.0, out["reason"], answer_text,
                       meta={"judge": which, "cost_usd": out["cost_usd"]})
