"""Cheap difficulty (easy/hard) features for the D9 routing cell. Uses only the prompt text and the (predicted) category."""
from __future__ import annotations

import re

import numpy as np

CATEGORIES = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")
FEATURE_NAMES = ("log_chars", "log_words", "n_sentences", "n_numbers", "n_lines", "n_list_items", "n_constraint_words",
                 "n_negations", "n_capitalised_names", "code_lines", "n_defs", "n_percent", "n_either_or")


def features(prompt: str) -> np.ndarray:
    words = prompt.split()
    code = "\n".join(ln for ln in prompt.splitlines() if re.match(r"^(\s{2,}|\t)\S|^\s*(def |return |for |while |if |import |class )", ln))
    f = [
        np.log1p(len(prompt)), np.log1p(len(words)),
        len(re.findall(r"[.!?](?:\s|$)", prompt)),
        len(re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", prompt)),
        len([ln for ln in prompt.splitlines() if ln.strip()]),
        len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+\S", prompt, re.M)),
        len(re.findall(r"\b(must|exactly|at most|no more than|at least|only|each|every|all|without|except|between|before|after|ahead of|immediately)\b", prompt, re.I)),
        len(re.findall(r"\b(not|never|no|n't|neither|nor)\b", prompt, re.I)),
        len(re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]+\b", prompt)),
        len([ln for ln in code.splitlines() if ln.strip()]),
        len(re.findall(r"\bdef \w+\(", prompt)),
        len(re.findall(r"%", prompt)),
        len(re.findall(r"\beither\b", prompt, re.I)),
    ]
    return np.array(f, dtype=float)


def category_onehot(cat: str) -> np.ndarray:
    return np.array([1.0 if c == cat else 0.0 for c in CATEGORIES])
