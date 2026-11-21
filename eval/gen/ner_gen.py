"""NER items: 35 built from sentence templates with known slots (gold by construction) + 15 hand-written
tricky ones. Convention (stated in the report): a span is the full proper name ("Bank of America" is one ORG,
no nested LOCATION); titles such as "Dr." are not part of a PERSON span; possessive 's is not part of a span;
DATE covers explicit calendar dates, month-year and years (no relative expressions).
"""

from __future__ import annotations

import random

PERSONS = ["Priya Nair", "Rahul Mehta", "Sofia Marquez", "Chen Wei", "Fatima Khan", "John Okafor", "Elena Petrova",
           "Hiroshi Tanaka", "Kwame Mensah", "Aisha Rahman", "Lars Eriksson", "Neha Sharma", "David Cohen",
           "Amara Singh", "Tomas Novak", "Yuki Sato", "Isabel Costa", "Omar Haddad", "Sunita Rao", "Vikram Joshi"]
ORGS = ["Infosys", "Tata Steel", "Siemens", "Google", "Reliance Industries", "Toyota", "World Bank", "Unilever",
        "Samsung", "Airbus", "Flipkart", "Nestle", "Microsoft", "Bank of America", "Stanford University",
        "University of Oxford", "Mahindra & Mahindra", "Deutsche Bank"]
LOCS = ["Pune", "Berlin", "Nairobi", "Tokyo", "Chennai", "Toronto", "Lagos", "Madrid", "Mumbai", "Sydney", "Cairo",
        "Oslo", "Brazil", "Kenya", "Germany", "Kerala", "Texas", "Lisbon", "Hanoi", "Dubai"]
DATES = ["3 March 2021", "March 3, 2021", "14 Feb 2019", "2020-07-15", "July 2022", "1998", "21st June 2023",
         "9 November 2017", "October 2015", "2024-01-30", "5th May 2016", "December 12, 2019"]
TYPE_OF = {"P": "PERSON", "O": "ORG", "L": "LOCATION", "D": "DATE"}

EASY_T = [
    "{P1} works at {O1}.",
    "{O1} opened a new office in {L1}.",
    "The conference in {L1} begins on {D1}.",
    "{P1} was born in {L1}.",
    "{O1} announced its quarterly results on {D1}.",
    "{P1} joined {O1} in {D1}.",
]
HARD_T = [
    "On {D1}, {P1} left {O1} to join {O2} in {L1}.",
    "{P1} and {P2} flew from {L1} to {L2} for a {O1} meeting in {D1}.",
    "After {P1}'s talk in {L1}, {O1} and {O2} signed a deal that was announced on {D1}.",
    "{O1}'s chief executive {P1} told reporters in {L1} that the plant would open in {D1}.",
    "{P2}, who studied at {O1} in {L1}, first met {P1} on {D1}.",
    "Between {L1}, {L2} and {L3}, {P1} visited several {O1} offices before {D1}.",
]
PROMPTS = [
    ("instruction", "Extract all named entities with their types (PERSON, ORG, LOCATION, DATE) from: '{s}'"),
    ("imperative", "Tag the people, organisations, places and dates in this sentence: {s}"),
    ("casual", "who/what/where/when is mentioned here? list the entities and their types: \"{s}\""),
    ("embedded", "Here's a line from a news article:\n\n{s}\n\nPull out every person, organisation, location and date it mentions, with the type of each."),
]

# (sentence, [(text, type)...], note)
HAND = [
    ("Jordan Peterson met Jordan's king in Amman.", [("Jordan Peterson", "PERSON"), ("Jordan", "LOCATION"), ("Amman", "LOCATION")],
     "'Jordan' is a person's name in the first span and the country in the second; possessive 's is not part of the span."),
    ("Ford announced that Henry Ford's grandson would visit Detroit in 2019.",
     [("Ford", "ORG"), ("Henry Ford", "PERSON"), ("Detroit", "LOCATION"), ("2019", "DATE")],
     "Same surname as company and person; the company 'Ford' is the subject of the announcement."),
    ("Amazon expanded its warehouse network along the Amazon River in 2021.",
     [("Amazon", "ORG"), ("Amazon River", "LOCATION"), ("2021", "DATE")], "Company vs river with the same word."),
    ("The Delhi Capitals beat the Mumbai Indians in Dubai on 5 April 2022.",
     [("Delhi Capitals", "ORG"), ("Mumbai Indians", "ORG"), ("Dubai", "LOCATION"), ("5 April 2022", "DATE")],
     "Sports teams named after cities are ORG; the whole team name is one span."),
    ("Georgia Smith moved from Georgia to Paris in March 2015.",
     [("Georgia Smith", "PERSON"), ("Georgia", "LOCATION"), ("Paris", "LOCATION"), ("March 2015", "DATE")],
     "First name that is also a place name."),
    ("Tata Consultancy Services hired Anand Rajan in Bengaluru on 1 June 2020.",
     [("Tata Consultancy Services", "ORG"), ("Anand Rajan", "PERSON"), ("Bengaluru", "LOCATION"), ("1 June 2020", "DATE")],
     "Organisation named after a family name."),
    ("Apple's iPhone sales in India rose after Tim Cook visited Mumbai in April 2023.",
     [("Apple", "ORG"), ("India", "LOCATION"), ("Tim Cook", "PERSON"), ("Mumbai", "LOCATION"), ("April 2023", "DATE")],
     "Product name 'iPhone' is not one of the four types, so it is not tagged."),
    ("Lionel Messi joined Inter Miami in July 2023 after leaving Paris Saint-Germain.",
     [("Lionel Messi", "PERSON"), ("Inter Miami", "ORG"), ("July 2023", "DATE"), ("Paris Saint-Germain", "ORG")],
     "Club names contain place names but are ORG as whole spans."),
    ("Nokia, founded in Finland, is now headquartered in Espoo.",
     [("Nokia", "ORG"), ("Finland", "LOCATION"), ("Espoo", "LOCATION")], "Appositive clause between commas."),
    ("The World Health Organization, headquartered in Geneva, praised Kerala's response in 2021.",
     [("World Health Organization", "ORG"), ("Geneva", "LOCATION"), ("Kerala", "LOCATION"), ("2021", "DATE")],
     "'the' is excluded from the ORG span; possessive stripped from Kerala."),
    ("On 15 August 1947, Jawaharlal Nehru addressed the nation from Delhi.",
     [("15 August 1947", "DATE"), ("Jawaharlal Nehru", "PERSON"), ("Delhi", "LOCATION")], "Date at the start of the sentence."),
    ("Siemens Energy and BP agreed terms with Kenya's government in Nairobi on 2020-11-04.",
     [("Siemens Energy", "ORG"), ("BP", "ORG"), ("Kenya", "LOCATION"), ("Nairobi", "LOCATION"), ("2020-11-04", "DATE")],
     "ISO-formatted date; 'government' is not a named entity."),
    ("Mount Kilimanjaro in Tanzania was climbed by Amina Yusuf in January 2022.",
     [("Mount Kilimanjaro", "LOCATION"), ("Tanzania", "LOCATION"), ("Amina Yusuf", "PERSON"), ("January 2022", "DATE")],
     "Mountain with a title-like prefix is one LOCATION span."),
    ("Washington crossed the Delaware, according to historian Eric Foner of Columbia University.",
     [("Washington", "PERSON"), ("Delaware", "LOCATION"), ("Eric Foner", "PERSON"), ("Columbia University", "ORG")],
     "'Washington' here is the general (a person), not the city or state."),
    ("Dr. Kavita Rao of AIIMS Delhi presented the findings in Geneva on 12 May 2021.",
     [("Kavita Rao", "PERSON"), ("AIIMS Delhi", "ORG"), ("Geneva", "LOCATION"), ("12 May 2021", "DATE")],
     "Title 'Dr.' is excluded from the PERSON span (stated convention); 'AIIMS Delhi' is one ORG span."),
]


# sentence -> alternative acceptable readings (review decisions): list of full alternative entity sets
ALTERNATIVES = {
    "Siemens Energy and BP agreed terms with Kenya's government in Nairobi on 2020-11-04.": [
        [("Siemens Energy", "ORG"), ("BP", "ORG"), ("Kenya", "ORG"), ("Nairobi", "LOCATION"), ("2020-11-04", "DATE")]],
    "Dr. Kavita Rao of AIIMS Delhi presented the findings in Geneva on 12 May 2021.": [
        [("Kavita Rao", "PERSON"), ("AIIMS", "ORG"), ("Delhi", "LOCATION"), ("Geneva", "LOCATION"), ("12 May 2021", "DATE")]],
}


def build():
    rng = random.Random(31)
    items = []

    def fill(tpl):
        pools = {"P": rng.sample(PERSONS, 2), "O": rng.sample(ORGS, 2), "L": rng.sample(LOCS, 3), "D": rng.sample(DATES, 1)}
        ents, s = [], tpl
        order = []
        for key in ("P1", "P2", "O1", "O2", "L1", "L2", "L3", "D1"):
            if "{" + key + "}" in tpl:
                val = pools[key[0]][int(key[1]) - 1]
                s = s.replace("{" + key + "}", val)
                order.append((val, TYPE_OF[key[0]]))
        return s, order

    seen = set()
    for tpls, n, diff in ((EASY_T, 25, "easy"), (HARD_T, 10, "hard")):
        k = 0
        while k < n:
            tpl = tpls[k % len(tpls)]
            s, ents = fill(tpl)
            if s in seen:
                continue
            seen.add(s)
            for text, _ in ents:
                assert text in s
            style, ptpl = rng.choice(PROMPTS)
            items.append(dict(prompt=ptpl.format(s=s), gold={"entities": [{"text": t, "type": ty} for t, ty in ents]},
                              source="template", difficulty=diff, phrasing=style,
                              note=f"Built from a template with known slots: " + "; ".join(f"{t} = {ty}" for t, ty in ents) + "."))
            k += 1
    for s, ents, note in HAND:
        for text, _ in ents:
            assert text in s, (text, s)
        style, ptpl = rng.choice(PROMPTS)
        gold = {"entities": [{"text": t, "type": ty} for t, ty in ents]}
        if s in ALTERNATIVES:
            gold["alternatives"] = [{"entities": [{"text": t, "type": ty} for t, ty in alt]} for alt in ALTERNATIVES[s]]
            note += " Alternative reading accepted (ambiguous span)."
        items.append(dict(prompt=ptpl.format(s=s), gold=gold,
                          source="hand", difficulty="hard", phrasing=style, note=note))
    for it in items:
        it.update(category="ner", grader="ner_f1", split="unsplit",
                  gold_checks="template slots" if it["source"] == "template" else "hand-written, reviewed")
    rng.shuffle(items)
    for i, it in enumerate(items, 1):
        it["id"] = f"ner-{i:03d}"
    return items
