"""The router: route(prompt) -> Result.

  classify (hybrid: rules -> MiniLM) -> difficulty -> policy lookup -> run the plan, cheapest step first:
    solver  pure-Python parser, then the D13 translator (a small local model translates, Python solves; defers when unsure)
    local   the cell's local model, same system prompt as the benchmark; 30 s budget for the whole local layer; validators must pass
    api     the cell's model; blank / failed -> ONE retry on the next tier up (escalate_to = B1)
  OUT_OF_SCOPE -> straight to B1.

route() never raises: any failure moves to the next step; if every step fails the Result carries `error` and an empty answer.
Every step is recorded in `trace`. API answers are not validated (as in the Phase 4 replay): only an error or a blank reply escalates.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from eval.graders.formats import system_prompt
from router.config import RouterConfig
from router.models import ModelClient, Prices, kind_of
from router.policy import CATEGORIES as SYSTEM_CATEGORIES
from router.policy import OOS, SOLVER_CATEGORIES, Policy
from router.validators import validate

# Rough output allowance for B1 when estimating "what B1 would have cost" for a request B1 did not serve (low reasoning effort, D11).
EST_B1_REASONING_TOKENS = 300
# Out-of-scope requests have no benchmark system prompt: B1 gets a neutral one and the largest output budget.
OOS_SYSTEM = "You are a helpful assistant. Answer the request directly and completely."


@dataclass
class Result:
    prompt: str
    answer: str = ""
    category: str = ""
    difficulty: str = ""
    layer: str = "error"            # solver | local | api | error
    model: str = ""                 # model (or "python-solver") that produced the answer
    cost_usd: float = 0.0           # list-price cost of every paid call made for this request (failed attempts included)
    b1_cost_usd: float = 0.0        # actual B1 cost if B1 answered, else an estimate (see estimate_b1_cost)
    savings_usd: float = 0.0
    latency_ms: int = 0
    escalated: bool = False
    error: Optional[str] = None
    label_source: str = ""          # rule | embedding | embedding-threshold | given
    plan: list = field(default_factory=list)
    trace: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Router:
    def __init__(self, policy: Policy, client: ModelClient, labeler=None, cfg: Optional[RouterConfig] = None,
                 clock: Callable[[], float] = time.perf_counter):
        self.policy, self.client, self.cfg, self.clock = policy, client, cfg or RouterConfig(), clock
        self._labeler = labeler
        self.prices = getattr(client, "prices", None) or Prices(self.cfg.prices_path)

    # ------------------------------------------------------------------ public
    def route(self, prompt: str, labels: Optional[tuple] = None) -> Result:
        """`labels` = (category, difficulty) skips the classifiers (used by the replay-consistency test, which feeds either the true
        labels or the classifiers' predicted labels, and by callers that already know the category)."""
        t0 = self.clock()
        res = Result(prompt=prompt)
        try:
            self._route(prompt, labels, res)
        except Exception as e:  # noqa: BLE001 - the contract is: never raise
            res.error = f"internal error: {type(e).__name__}: {str(e)[:200]}"
            res.trace.append({"step": "internal", "ok": False, "error": res.error})
            if not res.answer:
                res.layer = "error"
        res.latency_ms = int((self.clock() - t0) * 1000)
        self._finish_costs(res)
        return res

    # ------------------------------------------------------------------ internals
    def labeler(self):
        if self._labeler is None:
            from router.labeler import Labeler
            self._labeler = Labeler()
        return self._labeler

    def _classify(self, prompt, labels, res):
        if labels is not None:
            res.category, res.difficulty, res.label_source = labels[0], labels[1], "given"
            return
        try:
            lab = self.labeler().label(prompt)
            res.category, res.difficulty, res.label_source = lab["category"], lab["difficulty"], lab["path"]
        except Exception as e:  # noqa: BLE001 - an unclassifiable prompt is safest at B1
            res.category, res.difficulty, res.label_source = OOS, "easy", "classifier-error"
            res.trace.append({"step": "classify", "ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"})

    def _route(self, prompt, labels, res):
        self._classify(prompt, labels, res)
        plan = self.policy.plan(res.category, res.difficulty, use_solvers=self.cfg.use_solvers)
        res.plan = [f"{s.kind}:{s.model}" if s.model else s.kind for s in plan.steps]
        local_used = 0.0   # seconds of the local budget spent so far (translator + local model share it)
        last_api_failed = False
        for i, step in enumerate(plan.steps):
            if step.kind == "solver":
                out = self._solver(prompt, res, local_used)
                local_used = out["local_used"]
                if out["answer"] is not None:
                    return self._accept(res, "solver", "python-solver" if out["how"] == "pure" else f"translator:{out['how']}", f"ANSWER: {out['answer']}")
            elif step.kind == "local":
                remaining = self.cfg.local_budget_s - local_used
                if remaining < 1.0:
                    res.trace.append({"step": "local", "model": step.model, "ok": False, "skipped": "local time budget exhausted"})
                    res.escalated = True
                    continue
                r = self.client.chat(step.model, system_prompt(res.category), prompt, self.cfg.local_max_tokens[res.category], timeout=remaining)
                local_used += (r.latency_ms or 0) / 1000.0
                entry = {"step": "local", "model": step.model, **r.to_dict()}
                if not r.ok:
                    entry.update(ok=False, why="timeout" if (r.error or "").startswith("timeout") else (r.error or "blank reply"))
                else:
                    v = validate(res.category, prompt, r.text)
                    entry.update(ok=v.ok, why="" if v.ok else "; ".join(v.problems))
                res.trace.append(entry)
                if entry["ok"]:
                    return self._accept(res, "local", step.model, r.text)
                res.escalated = True
            else:  # api
                r = self.client.chat(step.model, self._system(res.category), prompt, self._max_tokens(res.category), timeout=self.cfg.api_timeout_s)
                entry = {"step": "api", "role": step.role, "model": step.model, **r.to_dict()}
                entry.update(ok=r.ok, why="" if r.ok else (r.error or "blank reply"))
                res.trace.append(entry)
                if r.ok:
                    return self._accept(res, "api", step.model, r.text)
                res.escalated = True
                last_api_failed = True
        res.layer = "error"
        res.error = "every step failed" + (" (last API step failed)" if last_api_failed else "")

    def _accept(self, res, layer, model, text):
        res.layer, res.model, res.answer = layer, model, text
        res.error = None

    def _solver(self, prompt, res, local_used) -> dict:
        """Pure Python first (free, instant); then the D13 translator when enabled and the local budget allows. Never raises."""
        cat = res.category
        out = {"answer": None, "how": None, "local_used": local_used}
        if cat not in SOLVER_CATEGORIES:
            return out
        from router.solvers import translate as T
        try:
            if cat == "math":
                from router.solvers.math_solver import solve_math
                pure = solve_math(prompt)
            else:
                from router.solvers.logic_solver import solve_logic
                pure = solve_logic(prompt)
            if pure.answered:
                res.trace.append({"step": "solver", "how": "pure-python", "ok": True})
                return {**out, "answer": pure.answer, "how": "pure"}
            res.trace.append({"step": "solver", "how": "pure-python", "ok": False, "why": pure.reason})
        except Exception as e:  # noqa: BLE001
            res.trace.append({"step": "solver", "how": "pure-python", "ok": False, "why": f"{type(e).__name__}: {str(e)[:100]}"})
        tmodel = self.cfg.translators.get(cat)
        remaining = self.cfg.local_budget_s - local_used
        if not (self.cfg.use_translators and tmodel):
            return out
        if remaining < 1.0:
            res.trace.append({"step": "translator", "model": tmodel, "ok": False, "skipped": "local time budget exhausted"})
            return out
        label, system, num_predict = ("Problem: ", T.MATH_SYSTEM, 256) if cat == "math" else ("Puzzle: ", T.LOGIC_SYSTEM, 800)
        r = self.client.chat(tmodel, system, label + prompt, num_predict, timeout=remaining, json_mode=(cat == "logic"))
        out["local_used"] = local_used + (r.latency_ms or 0) / 1000.0
        entry = {"step": "translator", "model": tmodel, **r.to_dict()}
        if not r.ok:
            entry.update(ok=False, why=r.error or "blank reply")
        else:
            tr = T.parse_math_translation(r.text, prompt) if cat == "math" else T.parse_logic_translation(r.text, prompt)
            entry.update(ok=tr.answered, why=tr.reason)
            if tr.answered:
                out.update(answer=tr.answer, how=tmodel)
        res.trace.append(entry)
        return out

    @staticmethod
    def _system(category):
        return system_prompt(category) if category in SYSTEM_CATEGORIES else OOS_SYSTEM

    def _max_tokens(self, category):
        return self.cfg.max_tokens.get(category, max(self.cfg.max_tokens.values()))

    # ------------------------------------------------------------------ cost
    def estimate_b1_cost(self, prompt: str, category: str, answer: str) -> float:
        """What B1 would have cost for this request: chars/4 token estimate for the input, answer length + a reasoning allowance for the output."""
        tin = (len(self._system(category)) + len(prompt)) // 4
        tout = len(answer) // 4 + EST_B1_REASONING_TOKENS
        return self.prices.cost(self.policy.b1, tin, tout)

    def _finish_costs(self, res: Result):
        res.cost_usd = sum(e.get("cost_usd") or 0.0 for e in res.trace if e.get("step") in ("api", "local", "translator"))
        try:
            if res.layer == "api" and res.model == self.policy.b1 and not res.escalated:
                res.b1_cost_usd = res.cost_usd
            else:
                res.b1_cost_usd = self.estimate_b1_cost(res.prompt, res.category, res.answer)
            res.savings_usd = res.b1_cost_usd - res.cost_usd
        except Exception:  # noqa: BLE001
            pass


def build_router(cfg: Optional[RouterConfig] = None, client: Optional[ModelClient] = None, labeler=None, policy: Optional[Policy] = None) -> Router:
    """Production wiring: policy from cfg.policy_path, live model client."""
    cfg = cfg or RouterConfig()
    if client is None:
        from router.models import LiveClient
        client = LiveClient(cfg)
    return Router(policy or Policy.load(cfg.policy_path), client, labeler, cfg)


_DEFAULT: Optional[Router] = None


def route(prompt: str, labels: Optional[tuple] = None) -> Result:
    """Module-level convenience: route one prompt with the production wiring (policy from RouterConfig, live clients). Never raises."""
    global _DEFAULT
    try:
        if _DEFAULT is None:
            _DEFAULT = build_router()
        return _DEFAULT.route(prompt, labels)
    except Exception as e:  # noqa: BLE001 - e.g. the policy file is unreadable
        return Result(prompt=prompt, error=f"router unavailable: {type(e).__name__}: {str(e)[:200]}")
