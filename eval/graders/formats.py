"""Fixed per-category answer-format instructions (Phase 1 plan section 3).

The SAME text is sent as the system prompt to every model, local or paid, so the comparison is fair
and the graders can rely on a predictable shape. Graders still have lenient fallbacks.
"""

from __future__ import annotations

CATEGORIES = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")

FORMAT_INSTRUCTIONS = {
    "math": (
        "Solve the problem. You may show brief working. "
        "End with a final line exactly of the form `ANSWER: <number>` "
        "(digits only, no units, no commas)."
    ),
    "logic": (
        "Solve the puzzle. You may show brief working. "
        "End with a final line exactly of the form `ANSWER: <value>`, "
        "where <value> is only the name/item/position asked for."
    ),
    "sentiment": (
        "Classify the sentiment as exactly one of: positive, negative, mixed, neutral. "
        "Give a one-sentence reason, then end with a final line exactly of the form "
        "`ANSWER: <label>`."
    ),
    "ner": (
        "Extract the named entities. Return only JSON: a list of objects "
        '{"text": "<exact span>", "type": "PERSON|ORG|LOCATION|DATE"}. No other text.'
    ),
    "code_debug": (
        "Find the bug and return only the corrected function, complete, in a single Python code "
        "block. No explanation outside the code block."
    ),
    "code_gen": (
        "Return only the requested function in a single Python code block, with the exact name and "
        "signature given. No explanation outside the code block."
    ),
    "summarisation": (
        "Follow the length/format constraint in the request exactly. Use only facts stated in the "
        "text; do not add anything. Return only the summary."
    ),
    "factual": (
        "Answer accurately and concisely, in at most 120 words. Do not pad."
    ),
}


def system_prompt(category: str) -> str:
    return FORMAT_INSTRUCTIONS[category]


def build_messages(category: str, prompt: str) -> list:
    """Chat messages used for every model in every phase."""
    return [{"role": "system", "content": FORMAT_INSTRUCTIONS[category]},
            {"role": "user", "content": prompt}]
