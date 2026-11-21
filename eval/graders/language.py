"""D10 language check: an answer that contains non-English script FAILS, independent of the judge.

Letters are classified by Unicode name. Latin (including accented letters) and Greek (pi, mu, Delta show up in
maths) are allowed; letters of any other script (CJK, kana, Hangul, Cyrillic, Arabic, Hebrew, Indic, Thai ...)
make the answer fail. Chain-of-thought inside <think> tags is ignored; only the answer text counts.
"""

from __future__ import annotations

import re
import unicodedata

from .common import strip_thinking

ALLOWED_SCRIPTS = {"LATIN", "GREEK"}

# Phase 3 fix: flag only letters of a real non-English SCRIPT. The earlier rule (first word of the Unicode name not
# Latin/Greek) also flagged letter-like symbols that appear in correct technical answers: micro sign (um), Planck
# constant, modifier/superscript letters (K^T, e^nt). Those are not another language, so they no longer fail.
OTHER_SCRIPTS = re.compile(
    r"CYRILLIC|CJK|HIRAGANA|KATAKANA|HANGUL|BOPOMOFO|ARABIC|HEBREW|DEVANAGARI|BENGALI|GURMUKHI|GUJARATI|ORIYA|TAMIL|"
    r"TELUGU|KANNADA|MALAYALAM|SINHALA|THAI|LAO|TIBETAN|MYANMAR|GEORGIAN|ARMENIAN|ETHIOPIC|KHMER|MONGOLIAN|SYRIAC|"
    r"THAANA|CHEROKEE|YI |HANGZHOU|IDEOGRAPH")


def script_of(ch: str) -> str:
    return unicodedata.name(ch, "").split(" ")[0]


def is_other_script(ch: str) -> bool:
    return bool(OTHER_SCRIPTS.search(unicodedata.name(ch, "")))


def non_english_chars(text: str) -> list:
    """Distinct letters (in order of appearance) from a script other than Latin/Greek."""
    out = []
    for ch in strip_thinking(text or ""):
        if ord(ch) > 127 and ch.isalpha() and is_other_script(ch) and ch not in out:
            out.append(ch)
    return out


def has_non_english_script(text: str) -> bool:
    return bool(non_english_chars(text))
