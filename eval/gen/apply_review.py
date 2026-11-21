"""One-off edits applying the review decisions to the item source files (run once, idempotent)."""

import re
from pathlib import Path

G = Path(__file__).resolve().parent

# --- sent-010: replace the ambiguous triage note with an unambiguous neutral item
p = G / "items_sentiment_factual.py"
s = p.read_text(encoding="utf-8")
old = """    ("Customer says the product 'broke' - please confirm the serial number before we open a claim.", U, H, "message", "Process request; the quoted 'broke' is reported, not an expressed feeling."),"""
new = """    ("The tool does what the documentation says. I haven't tried the alternatives, so I can't say whether it's worth the price.", U, H, "review", "States only that it matches its documentation and explicitly withholds any verdict on value."),"""
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")

# --- summaries: trim key facts that do not fit a 25-word limit
p = G / "items_summary.py"
s = p.read_text(encoding="utf-8")
reps = [
    ('["Imani Okafor won the Haldane Prize for proving a conjecture about primes", "proof checked by three teams over four months", "will donate part of the 100,000 dollar prize to mentor girls"], [["Okafor", "prime"], ["three", "four months", "62"], ["100,000", "mentor"]]',
     '["Imani Okafor won the Haldane Prize for proving a conjecture about primes", "will donate part of the 100,000 dollar prize to mentor girls"], [["Okafor", "prime"], ["100,000", "mentor"]]'),
    ('"9 of 24 km, volunteers run steam trains"', '"only 9 of the 24 km will carry trains"'),
    ('["Voss and Rhee debated; Voss cites unemployment cut from 8 to 5 percent", "Rhee promises a 12 percent minimum wage rise", "poll 46 to 44 percent, within margin of error"], [["unemployment", "8 to 5"], ["12 percent", "minimum wage"], ["46", "44"]]',
     '["Voss cites unemployment cut from 8 to 5 percent", "Rhee promises a 12 percent minimum wage rise"], [["unemployment", "8 to 5"], ["12 percent", "minimum wage"]]'),
]
for a, b in reps:
    if a in s:
        s = s.replace(a, b)
    else:
        assert b in s, a[:60]
p.write_text(s, encoding="utf-8")

# --- NER: alternatives for ner hand items (Kenya, AIIMS)
p = G / "ner_gen.py"
s = p.read_text(encoding="utf-8")
if "ALTERNATIVES" not in s:
    s = s.replace("def build():", '''# sentence -> alternative acceptable readings (review decisions): list of full alternative entity sets
ALTERNATIVES = {
    "Siemens Energy and BP agreed terms with Kenya's government in Nairobi on 2020-11-04.": [
        [("Siemens Energy", "ORG"), ("BP", "ORG"), ("Kenya", "ORG"), ("Nairobi", "LOCATION"), ("2020-11-04", "DATE")]],
    "Dr. Kavita Rao of AIIMS Delhi presented the findings in Geneva on 12 May 2021.": [
        [("Kavita Rao", "PERSON"), ("AIIMS", "ORG"), ("Delhi", "LOCATION"), ("Geneva", "LOCATION"), ("12 May 2021", "DATE")]],
}


def build():''', 1)
    s = s.replace('''        items.append(dict(prompt=ptpl.format(s=s), gold={"entities": [{"text": t, "type": ty} for t, ty in ents]},
                          source="hand", difficulty="hard", phrasing=style, note=note))''',
                  '''        gold = {"entities": [{"text": t, "type": ty} for t, ty in ents]}
        if s in ALTERNATIVES:
            gold["alternatives"] = [{"entities": [{"text": t, "type": ty} for t, ty in alt]} for alt in ALTERNATIVES[s]]
            note += " Alternative reading accepted (ambiguous span)."
        items.append(dict(prompt=ptpl.format(s=s), gold=gold,
                          source="hand", difficulty="hard", phrasing=style, note=note))''')
    p.write_text(s, encoding="utf-8")
print("applied")
