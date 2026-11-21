"""Task-type classifier: 8 categories + 'out_of_scope' (D9).

Four variants (compared in eval/phase4/eval_classifiers.py):
  (a) rule_classify        regex rules, ~microseconds, returns (label, strong) or (None, False)
  (b) EmbeddingClassifier  MiniLM embedding + logistic regression, with a max-probability threshold for out_of_scope
  (c) hybrid               strong rule first; otherwise the embedding classifier
  (d) llm_classify         zero-shot GLM call (free Hyde endpoint, priced at market rate in the reports)

The rules were hand-written from the category definitions (eval/graders/formats.py) and a first look at a few dev
prompts; they are not "learned" and so are not cross-validated. See eval/results/phase4/classifier_report.md.
"""
from __future__ import annotations

import re

import numpy as np

CATEGORIES = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")
OOS = "out_of_scope"
LABELS = CATEGORIES + (OOS,)

# ------------------------------------------------------------------ (a) rules
_OOS_RULES = [
    r"\b(build|create|develop|design|make|code)\b[^.?!]{0,60}\b(whole|complete|full|entire|end-to-end)\b[^.?!]{0,40}\b(website|web ?app|app|application|platform|system|pipeline|store|site)\b",
    r"\b(build|create|develop)\b[^.?!]{0,30}\b(a|an|me a|me an)\b[^.?!]{0,30}\b(website|mobile app|web app|e-commerce|platform|machine learning pipeline)\b",
    r"\b(write|compose|draft)\b[^.?!]{0,40}\b(essay|poem|short story|story|song|lyrics|speech|cover letter|blog post|business plan|screenplay|novel)\b",
    r"\btranslate\b[^.?!]{0,80}\b(into|to)\b\s+(french|spanish|german|japanese|hindi|chinese|italian|portuguese|russian|arabic|korean|latin)\b",
    r"\b(plan|itinerary|schedule)\b[^.?!]{0,40}\b(trip|vacation|holiday|wedding|study schedule|meal plan|\d+-?(day|week|month))\b",
    r"\b(\d{3,5})[- ]?words?\b",
    r"^\s*(hi|hello|hey|thanks|thank you|good (morning|evening))\b[\s,!.]",
    r"\b(how's|how is) your day\b|\byour favou?rite\b|\bdo you ever\b|\bare you (a|an|alive|sentient)\b",
    r"\b(role-?play|pretend to be|stay in character)\b",
    r"\b(generate|draw|paint|create)\b[^.?!]{0,30}\b(picture|image|logo|illustration|photo)\b",
    r"\b(create|make|build)\b[^.?!]{0,30}\b(presentation|slide deck|\d+ slides)\b",
    r"\b(marketing strategy|content calendar|project plan|technical specification)\b",
    r"\b(book|schedule|open)\b[^.?!]{0,30}\b(appointment|calendar|my inbox)\b",
]
_RULES = [  # (label, strong, pattern); first match wins, so order matters
    ("logic", True, r"\bfinished a race\b|\beach (own|owns|ordered) a different\b|\bwho (finished|owns|ordered)\b|\bknights?\b.*\bknaves?\b|\bno ties\b"),
    ("ner", True, r"\bnamed entit|\bextract\b[^.?!]{0,40}\b(entities|people|names|organi[sz]ations|locations|dates|places)\b|\bPERSON\b.*\bORG\b|\b(list|identify|find)\b[^.?!]{0,30}\b(people|organi[sz]ations|companies|locations|dates)\b[^.?!]{0,30}\b(mentioned|in the (text|sentence|passage))"),
    ("sentiment", True, r"\bsentiment\b|\b(positive|negative)\b[^.?!]{0,30}\b(neutral|mixed|negative|positive)\b|\bis (this|the) (review|comment|feedback|message|tweet)\b[^.?!]{0,30}\b(positive|negative|happy|upset)\b|\btone of (this|the) (review|comment)\b"),
    ("summarisation", True, r"\bsummari[sz]e\b|\bsummary\b|\bcondense\b|\btl;?dr\b|\bshorten\b|\bbullet points?\b|\bin (exactly |just )?(one|two|three|\d+) sentences?\b|\b(no more than|at most|under|within) \d+ words\b"),
    ("code_debug", True, r"\b(bug|buggy|debug|fix (the|this|my)|what'?s wrong|is wrong|incorrect|fails? (on|for|when)|doesn'?t work|does not work|wrong output|off-by-one|returns? the wrong)\b[\s\S]*(def |```|return |for |while )"),
    ("code_debug", True, r"(def |```)[\s\S]*\b(bug|buggy|fix|wrong|incorrect|fails?)\b"),
    ("code_gen", True, r"\b(write|implement|create|code|define|complete)\b[^.?!]{0,50}\b(function|method|python function|def)\b|\bdef \w+\(.*\)\s*(->.*)?:?\s*$|\bsignature\b"),
    ("math", False, r"\b(percent|percentage|ratio|discount|how many|how much|calculate|compute|total|change|per hour|every \d+ min|growth|grows?|shrank|profit|interest)\b[\s\S]*\d|\d[\s\S]*\b(percent|ratio|discount|how many|how much|calculate|total|change)\b|\d+\s*%"),
    ("factual", False, r"^\s*(what|why|how|when|who|where|which|explain|describe|define|is|does|do|are|was|were)\b"),
]
_OOS_RE = [re.compile(p, re.I) for p in _OOS_RULES]
_RULE_RE = [(lab, strong, re.compile(p, re.I)) for lab, strong, p in _RULES]


def rule_classify(prompt: str):
    """-> (label or None, strong). OOS rules run first; a weak match (math/factual) is a hint, not a decision."""
    head = prompt[:400]
    for rx in _OOS_RE:
        if rx.search(head):
            return OOS, True
    for lab, strong, rx in _RULE_RE:
        if rx.search(prompt):
            return lab, strong
    return None, False


# ------------------------------------------------------------------ (b) embedding + logistic regression
class EmbeddingClassifier:
    """MiniLM embedding (precomputed, passed in) + logistic regression over the 8 categories.
    A prompt whose top probability is below `threshold` is called out_of_scope."""

    def __init__(self, C: float = 10.0, threshold: float = 0.0):
        from sklearn.linear_model import LogisticRegression
        self.lr = LogisticRegression(C=C, max_iter=2000)
        self.threshold = threshold

    def fit(self, X, y):
        self.lr.fit(X, y)
        return self

    def proba(self, X):
        return self.lr.predict_proba(X)

    def predict(self, X):
        p = self.proba(X)
        lab = self.lr.classes_[p.argmax(1)]
        return np.where(p.max(1) < self.threshold, OOS, lab), p.max(1)


def pick_threshold(max_probs, budget: float = 0.05) -> float:
    """Threshold flagging at most `budget` of in-scope prompts (max-probs from inner cross-validation)."""
    return float(np.quantile(np.asarray(max_probs), budget))


# ------------------------------------------------------------------ (c) hybrid
def hybrid_predict(prompts, X, emb_clf: EmbeddingClassifier):
    """Strong rule first; otherwise the embedding classifier. Returns labels and which path decided."""
    emb_lab, _ = emb_clf.predict(X)
    out, path = [], []
    for p, e in zip(prompts, emb_lab):
        lab, strong = rule_classify(p)
        if lab is not None and strong:
            out.append(lab)
            path.append("rule")
        else:
            out.append(e)
            path.append("embedding")
    return out, path


class HybridClassifier:
    """Deployable default: strong rule first, else embedding LR with the out_of_scope threshold.
    Weights come from router/artifacts/task_type_lr.npz (fit on all 240 dev prompts by eval/phase4/eval_classifiers.py).
    The caller supplies the MiniLM embedding (router.embeddings in tests; sentence-transformers in the service)."""

    def __init__(self, coef, intercept, classes, threshold):
        self.coef, self.intercept, self.classes, self.threshold = coef, intercept, list(classes), float(threshold)

    @classmethod
    def load(cls, path=None):
        from pathlib import Path
        p = Path(path) if path else Path(__file__).resolve().parent / "artifacts" / "task_type_lr.npz"
        z = np.load(p, allow_pickle=False)
        return cls(z["coef"], z["intercept"], z["classes"].tolist(), float(z["threshold"]))

    def proba(self, vec):
        s = self.coef @ np.asarray(vec, float) + self.intercept
        s = s - s.max()
        e = np.exp(s)
        return e / e.sum()

    def predict(self, prompt: str, vec) -> dict:
        lab, strong = rule_classify(prompt)
        if lab is not None and strong:
            return {"label": lab, "path": "rule", "confidence": 1.0}
        p = self.proba(vec)
        i = int(p.argmax())
        if p[i] < self.threshold:
            return {"label": OOS, "path": "embedding-threshold", "confidence": float(p[i])}
        return {"label": self.classes[i], "path": "embedding", "confidence": float(p[i])}


# ------------------------------------------------------------------ (d) LLM classifier
LLM_SYSTEM = (
    "You are a prompt router. Classify the user's prompt into exactly one label:\n"
    "factual: a general-knowledge question or explanation request\n"
    "math: an arithmetic / percentage / ratio / rate word problem to compute\n"
    "sentiment: classify the sentiment of a given text (positive/negative/mixed/neutral)\n"
    "summarisation: summarise a given passage under a length or format limit\n"
    "ner: extract named entities (people, organisations, places, dates) from a text\n"
    "code_debug: find and fix a bug in code that is given\n"
    "logic: a deductive puzzle (who owns what / who finished where)\n"
    "code_gen: write one function from a specification\n"
    "out_of_scope: anything else, or any request much bigger than the above (whole apps or websites, long essays, "
    "stories, translation, travel or business plans, images, chit-chat, multi-part projects)\n"
    "Reply with only the label."
)
LLM_PRICE = (0.15, 0.50)  # USD per 1M tokens, market rate for glm-5.3-flash (model_prices.json)


def parse_llm_label(text: str) -> str:
    t = (text or "").lower()
    best, pos = None, None
    for lab in LABELS:
        for form in (lab, lab.replace("_", " "), lab.replace("_", "-")):
            i = t.find(form)
            if i >= 0 and (pos is None or i < pos):
                best, pos = lab, i
    return best or OOS  # an unparsable reply is treated as out of scope (safe: goes to B1)


def llm_classify(prompt: str, model: str = "hyde/glm-5.3-flash") -> dict:
    """One zero-shot classification call. Returns {label, raw, tokens_in, tokens_out, latency_s, cost_usd}."""
    import time

    import httpx

    from src.config import get_settings

    s = get_settings()
    payload = {"model": model, "temperature": 0.0, "max_tokens": 600, "reasoning_effort": "low",
               "messages": [{"role": "system", "content": LLM_SYSTEM}, {"role": "user", "content": prompt[:6000]}]}
    last = ""
    for k in range(4):
        t0 = time.time()
        try:
            r = httpx.post(s.hyde_base_url.strip().rstrip("/") + "/chat/completions", json=payload, timeout=120,
                           headers={"Authorization": f"Bearer {s.hyde_api_key.strip()}"})
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(3 * (k + 1))
                continue
            r.raise_for_status()
            d = r.json()
            text = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            u = d.get("usage") or {}
            tin, tout = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
            if not text.strip() and k < 3:
                last = "empty"
                time.sleep(2)
                continue
            return {"label": parse_llm_label(text), "raw": text.strip()[:80], "tokens_in": tin, "tokens_out": tout,
                    "latency_s": time.time() - t0, "cost_usd": (tin * LLM_PRICE[0] + tout * LLM_PRICE[1]) / 1e6}
        except httpx.HTTPError as e:
            last = str(e)[:100]
            time.sleep(3 * (k + 1))
    return {"label": OOS, "raw": f"FAILED {last}", "tokens_in": 0, "tokens_out": 0, "latency_s": 0.0, "cost_usd": 0.0}
