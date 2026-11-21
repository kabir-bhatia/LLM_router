"""Required vs optional key points for the factual items (review systemic fix 2).

Rule: REQUIRED = what a correct, concise answer to the exact question must contain. Everything else
(background, caveats, nice-to-have mechanism) is OPTIONAL and never decides pass/fail.
OPT_IDX moves existing key points (by index) to optional; OVERRIDE rewrites the split where the point text
itself mixed required and optional content. build() returns the audit log used in the Phase 1 report.
"""

OPT_IDX = {
    "What does DNS do?": [1],
    "What is the difference between a virus and a bacterium?": [2],
    "Why does the Moon have phases?": [1],
    "Explain what an API is.": [2],
    "What was the Industrial Revolution?": [2],
    "How do vaccines work?": [2],
    "What is compound interest?": [1],
    "What causes the seasons on Earth?": [2],
    "What was the French Revolution?": [2],
    "What is the greenhouse effect?": [2],
    "What is a black hole?": [1],
    "What do mitochondria do in a cell?": [1],
    "What was the Cold War?": [2],
    "Does the Coriolis effect decide which way water spins down a bathtub drain?": [1, 2],
    "What were the main causes of the 2008 global financial crisis?": [2],
    "How does public-key cryptography let two strangers communicate securely?": [2],
    "What does the Heisenberg uncertainty principle say?": [1],
    "When and how did the Western Roman Empire end?": [2],
    "What is the difference between correlation and causation?": [2],
    "What is the difference between a recession and a depression?": [2],
    "Why does ice float on liquid water?": [1],
    "What was the significance of the Magna Carta of 1215?": [2],
    "How do mRNA vaccines work?": [2],
    "What is opportunity cost?": [1],
    "Why is the speed of light central to special relativity?": [2],
    "What caused the Dust Bowl in the 1930s United States?": [2],
    "How does a heat pump work, and why can it deliver more heat than the electrical energy it uses?": [0],
    "What is the difference between nominal and real interest rates?": [2],
    "What is a race condition in programming?": [2],
}

OVERRIDE = {
    "Explain the water cycle.": (["evaporation", "condensation into clouds", "precipitation"],
                                 ["collection in oceans, rivers, lakes and groundwater"]),
    "How does the attention mechanism in a transformer model work?": (
        ["each token weighs the relevance of other tokens", "output is a weighted sum of value vectors"],
        ["uses queries, keys and values", "captures long-range dependencies in parallel"]),
    "What is a hash function, and why is that useful for storing passwords?": (
        ["maps input to fixed-size output deterministically", "one-way: hard to invert",
         "systems store password hashes rather than plaintext"],
        ["salting the hash"]),
}

# questions where every original key point stays required (checked against the rule, nothing moved)
KEPT_ALL = [
    "Explain what photosynthesis is.", "What is inflation?", "What is a dividend?", "What does GDP measure?",
    "What is machine learning?", "What is the difference between weather and climate?", "What is a bond in finance?",
    "Why is the sky blue and not violet?", "What was the Peace of Westphalia (1648) known for?",
    "What is encryption?", "What does the Pythagorean theorem state?", "Why is the sky blue?",
    "What is a CPU cache and why does it exist?", "What is the difference between TCP and UDP?",
    "Why do central banks raise interest rates to fight inflation, and what is the main trade-off?",
    "What does the CAP theorem state?", "What is the difference between supervised and unsupervised learning?",
    "Why do we have leap years, and why aren't all years divisible by 4 leap years?",
]


def split(question: str, key_points: list):
    """Return (required, optional)."""
    if question in OVERRIDE:
        return OVERRIDE[question]
    idx = OPT_IDX.get(question, [])
    req = [k for i, k in enumerate(key_points) if i not in idx]
    opt = [k for i, k in enumerate(key_points) if i in idx]
    return req, opt


def audit_log(items):
    """items: list of (question, key_points). Returns markdown lines and asserts full coverage."""
    covered = set(OPT_IDX) | set(OVERRIDE) | set(KEPT_ALL)
    qs = {q for q, _ in items}
    assert qs <= covered, f"unaudited factual items: {qs - covered}"
    assert not (covered - qs), f"audit entries with no item: {covered - qs}"
    lines = []
    for q, kps in items:
        req, opt = split(q, kps)
        if opt:
            lines.append(f"- {q} -> optional: " + "; ".join(opt))
    return lines
