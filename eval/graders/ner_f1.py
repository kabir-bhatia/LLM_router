"""NER grader: entity-level F1 over (text, type) pairs; passes at F1 == 1.0.

Tolerant to case, spacing, leading 'the', type aliases and date format
(dates are normalised to ISO via a small parser, so '3 March 2021' == 'March 3, 2021').
Gold: {"entities": [{"text": "Priya Nair", "type": "PERSON"}, ...],
       "alternatives": [{"entities": [...]}, ...]}   # optional: other fully acceptable readings
Titles (Dr., Mr., ...) on PERSON spans and a trailing possessive 's are stripped before matching.
"""

from __future__ import annotations

import json
import re

from .common import GradeResult, strip_thinking

TYPE_ALIASES = {
    "PERSON": "PERSON", "PER": "PERSON", "PEOPLE": "PERSON",
    "ORG": "ORG", "ORGANIZATION": "ORG", "ORGANISATION": "ORG", "COMPANY": "ORG",
    "LOCATION": "LOCATION", "LOC": "LOCATION", "GPE": "LOCATION", "PLACE": "LOCATION",
    "DATE": "DATE", "TIME": "DATE",
}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9


def norm_date(s: str):
    """Normalise common date spellings to YYYY-MM-DD / YYYY-MM / YYYY; None if not a date."""
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s.strip().lower().replace(",", " "))
    t = re.sub(r"\bthe\b|\bof\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)  # day-first (Indian/UK) by convention
    if m:
        return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", t)
    if m and m[2] in MONTHS:
        return f"{int(m[3]):04d}-{MONTHS[m[2]]:02d}-{int(m[1]):02d}"
    m = re.fullmatch(r"([a-z]+) (\d{1,2}) (\d{4})", t)
    if m and m[1] in MONTHS:
        return f"{int(m[3]):04d}-{MONTHS[m[1]]:02d}-{int(m[2]):02d}"
    m = re.fullmatch(r"([a-z]+) (\d{4})", t)
    if m and m[1] in MONTHS:
        return f"{int(m[2]):04d}-{MONTHS[m[1]]:02d}"
    if re.fullmatch(r"\d{4}", t):
        return t
    return None


def norm_entity(text, etype):
    etype = TYPE_ALIASES.get(str(etype).strip().upper(), str(etype).strip().upper())
    t = re.sub(r"\s+", " ", str(text)).strip().casefold().strip(" .,;:\"'")
    if etype == "DATE":
        nd = norm_date(t)
        if nd:
            return nd, etype
    t = re.sub(r"^the ", "", t)
    if etype == "PERSON":  # titles are not part of a name span (stated convention)
        t = re.sub(r"^(?:dr|mr|mrs|ms|mx|prof|sir|shri|smt)\.?\s+", "", t)
    t = re.sub(r"[’']s$", "", t)  # possessive 's is not part of a span
    return t, etype


def _json_candidates(text: str):
    text = strip_thinking(text)
    for blk in re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE):
        yield blk
    yield text
    for op, cl in (("[", "]"), ("{", "}")):
        i, j = text.find(op), text.rfind(cl)
        if 0 <= i < j:
            yield text[i:j + 1]


def _bare_objects(cand: str):
    """A bare sequence of JSON objects, optionally comma-separated, with no enclosing [ ] (seen from
    qwen3:1.7b in the Phase 2 dry run). Returns the list of objects, or None if anything else is there."""
    dec, i, n, objs = json.JSONDecoder(), 0, len(cand), []
    while i < n:
        if cand[i].isspace() or cand[i] == ",":
            i += 1
            continue
        if cand[i] != "{":
            return None
        try:
            obj, i = dec.raw_decode(cand, i)
        except json.JSONDecodeError:
            return None
        objs.append(obj)
    return objs if len(objs) > 1 else None


def parse_entities(text: str):
    """Parse model output into normalised (text, type) pairs; None if no JSON found."""
    for cand in _json_candidates(text):
        try:
            data = json.loads(cand.strip())
        except (json.JSONDecodeError, ValueError):
            data = _bare_objects(cand.strip())
            if data is None:
                continue
        pairs = _from_json(data)
        if pairs is not None:
            return pairs
    return None


def _from_json(data):
    if isinstance(data, dict):
        for key in ("entities", "named_entities", "result", "results"):
            if key in data:
                return _from_json(data[key])
        if data and all(str(k).upper() in TYPE_ALIASES for k in data):
            out = []
            for k, v in data.items():
                vals = v if isinstance(v, list) else [v]
                out += [norm_entity(x, k) for x in vals if isinstance(x, str)]
            return out
        return None
    if isinstance(data, list):
        out = []
        for it in data:
            if isinstance(it, dict):
                txt = next((it[k] for k in ("text", "entity", "name", "value", "span") if k in it), None)
                typ = next((it[k] for k in ("type", "label", "category", "entity_type") if k in it), None)
                if txt is None or typ is None:
                    return None
                out.append(norm_entity(txt, typ))
            elif isinstance(it, (list, tuple)) and len(it) == 2:
                out.append(norm_entity(it[0], it[1]))
            else:
                return None
        return out
    return None


def _score(got: set, entities) -> tuple:
    want = {norm_entity(e["text"], e["type"]) for e in entities}
    tp = len(got & want)
    p = tp / len(got) if got else 0.0
    r = tp / len(want) if want else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return f1, p, r, want


def grade_ner(response: str, gold: dict) -> GradeResult:
    got_list = parse_entities(response)
    if got_list is None:
        return GradeResult(False, 0.0, "no parseable JSON entity list", None)
    got = set(got_list)
    readings = [gold["entities"]] + [a["entities"] for a in gold.get("alternatives", [])]
    best = max((_score(got, r) + (k,) for k, r in enumerate(readings)), key=lambda x: x[0])
    f1, p, r, want, which = best
    ok = f1 >= 1.0 - 1e-9
    return GradeResult(ok, f1, f"P={p:.2f} R={r:.2f} F1={f1:.2f}" + (f" (alternative {which})" if which else ""),
                       sorted(got), meta={"missing": sorted(want - got), "extra": sorted(got - want),
                                          "reading": which})
