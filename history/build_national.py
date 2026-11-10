"""Build national and state history from the Digest of Education Statistics tables.
Reads  hist raw digest files (all editions); newer editions win where years overlap.
Writes history/output/national.json and history/output/states.json"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "raw/digest")
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)


def editions(table: str):
    fs = sorted(RAW.glob(f"digest_d*_tabn{table}.xls*"), key=lambda p: p.name)
    return [(int(re.search(r"_d(\d\d)_", f.name).group(1)), f) for f in fs]


def year_of(h) -> int | None:
    """'2011-\\n12' or '2016-17 \\2,3\\' or 1989 -> fall year (2011, 2016, 1989)."""
    s = re.sub(r"\\[^\\]*\\", "", str(h)).replace("\n", "")
    m = re.search(r"((?:19|20)\d\d)", s)
    return int(m.group(1)) if m and len(s.strip()) <= 20 else None


def num(v):
    if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
        return float(v)
    s = str(v).strip().replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def clean_label(s) -> str:
    s = re.sub(r"\\[^\\]*\\", "", str(s))
    return re.sub(r"[ .]+$", "", s.strip()).strip()


CAT = {"Autism": "autism", "Deaf-blindness": "deafblind", "Developmental delay": "devdelay", "Emotional disturbance": "emotional",
       "Hearing impairment": "hearing", "Intellectual disability": "intellectual", "Multiple disabilities": "multiple",
       "Orthopedic impairment": "orthopedic", "Other health impairment": "otherhealth", "Preschool disabled": "preschool",
       "Specific learning disability": "learning", "Speech or language impairment": "speech", "Traumatic brain injury": "tbi",
       "Visual impairment": "visual", "All disabilities": "all"}


def cat_key(label: str):
    l = label.rstrip("s") if label.endswith("ments") or label.endswith("ties") else label
    for k, v in CAT.items():
        if label.lower().startswith(k.lower()) or l.lower().startswith(k.lower()):
            return v
    return None


def t20430():
    served, share, pct_enr = {}, {}, {}
    for ed, f in editions("204.30"):
        x = pd.read_excel(f, header=None)
        years = {c: year_of(x.iat[1, c]) for c in range(1, x.shape[1])}
        block, started = 0, False
        for i in range(3, x.shape[0]):
            lab = x.iat[i, 0]
            if pd.isna(lab):
                if started:
                    block += 1
                    started = False
                continue
            lab = clean_label(lab)
            k = cat_key(lab)
            if not k:
                continue
            started = True
            target = [served, share, pct_enr][min(block, 2)]
            for c, y in years.items():
                v = num(x.iat[i, c])
                if y and v is not None:
                    target.setdefault(y, {})[k] = v       # later editions overwrite
    return served, share, pct_enr


def t20460():
    """Share of school-age students with disabilities in each setting, all students. Year rows carry values directly,
    or (newer editions) a year row is followed by an 'All students with disabilities' row holding that year's values."""
    env = {}
    for ed, f in editions("204.60"):
        x = pd.read_excel(f, header=None)
        pending = None
        for i in range(4, x.shape[0]):
            lab = str(x.iat[i, 0]).strip()
            vals = [num(x.iat[i, c]) for c in range(1, min(x.shape[1], 10))]
            y = year_of(lab) if lab[:4].isdigit() else None
            if y:
                if vals[0] is None:
                    pending = y
                    continue
            elif lab.lower().startswith("all students with disab") and pending and vals[0] is not None:
                y, pending = pending, None
            else:
                continue
            env[y] = {"lt40": vals[1], "40_79": vals[2], "80plus": vals[3], "sep_school": vals[4], "residential": vals[5],
                      "private": vals[6] if len(vals) > 6 else None, "homebound": vals[7] if len(vals) > 7 else None}
    return env


def t21990():
    ex = {}
    for ed, f in editions("219.90"):
        x = pd.read_excel(f, header=None)
        for i in range(x.shape[0]):
            y = year_of(x.iat[i, 0])
            if y and 1990 < y < 2100 and str(x.iat[i, 0]).strip()[:4].isdigit():
                # next row with "Total number" then "Percentage distribution"
                for j in range(i + 1, min(i + 4, x.shape[0])):
                    if str(x.iat[j, 0]).strip().lower().startswith("percent"):
                        row = [num(x.iat[j, c]) for c in range(1, x.shape[1])]
                        row = [v for v in row if v is not None]
                        if len(row) >= 6:
                            ex[y] = {"regular": row[1], "alt_cert": row[2], "max_age": row[3], "dropout": row[4], "died": row[5]}
                        break
    return ex


def t20470():
    st = {}
    for ed, f in editions("204.70"):
        x = pd.read_excel(f, header=None)
        hdr_row = 2
        cols = {}
        for c in range(1, x.shape[1]):
            y = year_of(x.iat[hdr_row, c])
            if y and y not in cols.values():
                cols[c] = y
            elif x.iat[1, c] is not None and "3- to 5" in str(x.iat[1, c]):
                break
        # percent-of-enrollment columns are in a second block in older editions; keep counts here
        for i in range(4, x.shape[0]):
            name = clean_label(x.iat[i, 0])
            if not name or name.startswith("Table") or len(name) > 40:
                continue
            for c, y in cols.items():
                v = num(x.iat[i, c])
                if v is not None:
                    st.setdefault(name, {})[y] = v
    return st


def enrollment_by_state():
    """Public school enrollment by state and year (table 203.20), to turn counts into shares."""
    enr = {}
    for ed, f in editions("203.20"):
        x = pd.read_excel(f, header=None)
        hdr = None
        for i in range(0, 6):
            ys = [year_of(x.iat[i, c]) for c in range(1, x.shape[1])]
            if sum(1 for y in ys if y and 1960 < y < 2100) >= 5:
                hdr = i
                break
        if hdr is None:
            continue
        cols = {c: year_of(x.iat[hdr, c]) for c in range(1, x.shape[1])
                if "project" not in " ".join(str(x.iat[r, c]).lower() for r in range(0, hdr + 1))
                and "project" not in " ".join(str(x.iat[r, cc]).lower() for r in range(0, hdr) for cc in range(max(1, c - 12), c + 1) if str(x.iat[r, cc]) != "nan")[-60:]}
        for i in range(hdr + 1, x.shape[0]):
            name = clean_label(x.iat[i, 0])
            if not name or len(name) > 40:
                continue
            for c, y in cols.items():
                v = num(x.iat[i, c])
                if y and v is not None and y not in enr.get(name, {}):
                    enr.setdefault(name, {})[y] = v
    return enr


def main():
    served, share, pct = t20430()
    env, ex, stc, enr = t20460(), t21990(), t20470(), enrollment_by_state()
    nat = {"served_thousands": {y: v.get("all") for y, v in sorted(served.items())},
           "pct_enrollment": {y: v.get("all") for y, v in sorted(pct.items())},
           "by_category_thousands": {y: v for y, v in sorted(served.items())},
           "environments": dict(sorted(env.items())),
           "exits": {y: v for k, (y, v) in enumerate(sorted(ex.items())) if k == 0 or v != sorted(ex.items())[k - 1][1]}}
    (OUT / "national.json").write_text(json.dumps(nat, indent=1))
    states = {}
    for s, ys in stc.items():
        e = enr.get(s, {})
        states[s] = {y: {"served": v, "pct": round(100 * v / e[y], 2) if e.get(y) else None} for y, v in sorted(ys.items())}
    (OUT / "states.json").write_text(json.dumps(states, indent=1))
    print("served years", list(nat["served_thousands"].items()))
    print("pct", list(nat["pct_enrollment"].items()))
    print("env years", list(env)[:5], "...", list(env)[-3:], env.get(2022))
    print("exit years", list(ex.items()))
    print("states", len(states), list(states.get("New Jersey", {}).items()))
    print("enr NJ", list(enr.get("New Jersey", {}).items())[-8:])


main()
