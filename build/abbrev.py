"""Spell out the abbreviations in official district names, so a reader sees what "Abbott ISD" or "Allen County ESC" means.

The official name stays as the page heading. When an abbreviation can be expanded with confidence, the page adds a
"Full name" line. Several abbreviations mean different things in different states (ISD is an Independent School District
in Texas but an Intermediate School District in Michigan), so the table is by state. An abbreviation that is not listed
for a state is left as it is.
"""
from __future__ import annotations

import re

ANY = {  # the same meaning in every state where it appears
    "SD": "School District", "HS": "High School", "DIST": "District", "BOCES": "Board of Cooperative Educational Services",
    "RESA": "Regional Educational Service Agency",
}
BY_STATE = {
    "TX": {"ISD": "Independent School District", "CISD": "Consolidated Independent School District"},
    "MN": {"ISD": "Independent School District"},
    "MI": {"ISD": "Intermediate School District", "ESD": "Educational Service District"},
    "IL": {"CUSD": "Community Unit School District", "CCSD": "Community Consolidated School District", "HSD": "High School District",
           "CHSD": "Community High School District", "ESD": "Elementary School District", "USD": "Unit School District",
           "CUD": "Community Unit District", "UD": "Unit District", "PSD": "Public School District", "GSD": "Grade School District",
           "ROE": "Regional Office of Education", "ISC": "Intermediate Service Center"},
    "PA": {"CS": "Charter School", "CHS": "Charter High School", "IU": "Intermediate Unit", "AVTS": "Area Vocational-Technical School"},
    "ME": {"RSU": "Regional School Unit", "MSAD": "Maine School Administrative District", "CSD": "Community School District"},
    "NY": {"CSD": "Central School District"},
    "IA": {"CSD": "Community School District", "AEA": "Area Education Agency"},
    "CO": {"AU": "Administrative Unit"},
    "CA": {"ROP": "Regional Occupational Program", "JPA": "Joint Powers Authority", "USD": "Unified School District"},
    "KS": {"USD": "Unified School District"},
    "DC": {"PCS": "Public Charter School"},
    "OH": {"ESC": "Educational Service Center", "JVSD": "Joint Vocational School District"},
    "OR": {"ESD": "Education Service District"},
    "WA": {"ESD": "Educational Service District"},
    "IN": {"MSD": "Metropolitan School District"},
}


# Shortened words in federal name fields. Phrases first, then single words. Only clear cases: "Co" (County, Company,
# or Co-op) and one-off cut-offs such as "Livingstn" are left alone.
PHRASES = [(r"\bSp(?:ec)? Ed(?:uc)?\b", "Special Education"), (r"\bSpec Serv\b", "Special Services"), (r"\bVoc Ed(?:uc)?\b", "Vocational Education"),
           (r"\bServ (Ctr|Cntr)\b", r"Service \1"), (r"\bCons (SD|School|Schools)\b", r"Consolidated \1"), (r"\bJnt Agr\b", "Joint Agreement")]
WORDS = {"Educ": "Education", "Coop": "Cooperative", "Ctr": "Center", "Cntr": "Center", "Twp": "Township", "Reg": "Regional", "Voc": "Vocational",
         "Acad": "Academy", "Sch": "School", "Schl": "School", "Schs": "Schools", "Schls": "Schools", "Dist": "District", "Dists": "Districts",
         "Assoc": "Association", "Inst": "Institute", "Chtr": "Charter", "CHRTR": "Charter", "Elem": "Elementary", "Mt": "Mount", "Ft": "Fort",
         "Jnt": "Joint", "Serv": "Services", "CTR": "Center"}
STATE_WORDS = {"ME": {"Plt": "Plantation"}, "DC": {"Pcs": "Public Charter School"}}


STATE_NAMES: dict = {}   # code -> state name, filled by site.py; a district's own state code inside its name is spelled out


def full_name(name: str, state: str) -> str | None:
    """The name with known abbreviations spelled out, or None if nothing changed."""
    if not isinstance(name, str):
        return None
    table = {**ANY, **BY_STATE.get(state, {})}
    if state in STATE_NAMES and state not in table:
        table[state] = STATE_NAMES[state]
    out = re.sub(r"\b[A-Z]{2,5}\b", lambda m: table.get(m.group(0), m.group(0)), name)
    for pat, rep in PHRASES:
        out = re.sub(pat, rep, out)
    words = {**WORDS, **STATE_WORDS.get(state, {})}
    out = re.sub(r"\b[A-Za-z]{2,6}\b", lambda m: words.get(m.group(0), m.group(0)), out)
    return out if out != name else None
