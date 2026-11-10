"""Out-of-school suspension over time, by district, from the Civil Rights Data Collection.
School files summed to districts, as the atlas does for 2023-24. Students with IEPs (IDEA) and students without
disabilities, each per 100 students in that group. Years: 2013-14, 2015-16, 2017-18, 2020-21, 2021-22.
Negative codes (not applicable, suppressed) are read as 0 for a school, matching how the files mark schools without
the item; a district-year needs at least 10 students in the group.
Writes history/output/district_disc.json: {leaid: {"i": {fall_year: rate}, "n": {fall_year: rate}}}"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "raw/crdc")
OUT = Path(__file__).resolve().parent / "output"
RACES = ("HI", "AM", "AS", "HP", "BL", "WH", "TR")


def frames(year: int):
    z = zipfile.ZipFile(RAW / f"{year}-{str(year + 1)[2:]}.zip")
    names = z.namelist()
    if year == 2013:
        sus = next(n for n in names if n.endswith("11-2 Suspensions (required elements).xlsx"))
        enr = next(n for n in names if n.endswith("03 Enrollment.xlsx"))
        rd = lambda n: pd.read_excel(io.BytesIO(z.read(n)), dtype=str)
        return rd(sus), rd(enr)
    if year == 2015:
        n = next(n for n in names if n.endswith("CRDC 2015-16 School Data.csv"))
        head = pd.read_csv(z.open(n), nrows=0, encoding="latin-1").columns
        keep = [c for c in head if c == "LEAID" or re.search(r"(OOS|IDEAENR|ENR_IDEA|TOT_ENR|504ENR|ENR_504)", c)]
        df = pd.read_csv(z.open(n), dtype=str, encoding="latin-1", usecols=keep)
        return df, df
    sus = next(n for n in names if re.search(r"(SCH|School)/(CRDC/CSV/)?Suspensions\.csv$", n))
    enr = next(n for n in names if re.search(r"(SCH|School)/(CRDC/CSV/)?Enrollment\.csv$", n))
    def rd(n):
        head = pd.read_csv(z.open(n), nrows=0, encoding="latin-1").columns
        keep = [c for c in head if c == "LEAID" or re.search(r"(OOS|IDEAENR|ENR_IDEA|TOT_ENR|504ENR|ENR_504)", c)]
        return pd.read_csv(z.open(n), dtype=str, encoding="latin-1", usecols=keep)
    return rd(sus), rd(enr)


def total(df, tot_stems, race_stems):
    cols = [f"{s}_{x}" for s in tot_stems for x in ("M", "F", "X") if f"{s}_{x}" in df.columns]
    if not cols:
        cols = [f"{s}_{r}_{x}" for s in race_stems for r in RACES for x in ("M", "F") if f"{s}_{r}_{x}" in df.columns]
    if not cols:
        return None
    v = df[cols].apply(pd.to_numeric, errors="coerce")
    return v.where(v > 0, 0).sum(axis=1)


def main():
    OUT.mkdir(exist_ok=True)
    res = {}
    for y in (2013, 2015, 2017, 2020, 2021):
        sus, enr = frames(y)
        lid_s = sus.LEAID.astype(str).str.strip().str.zfill(7)
        lid_e = enr.LEAID.astype(str).str.strip().str.zfill(7)
        oi = total(sus, ["TOT_DISCWDIS_SINGOOS_IDEA", "TOT_DISCWDIS_MULTOOS_IDEA"], ["SCH_DISCWDIS_SINGOOS_IDEA", "SCH_DISCWDIS_MULTOOS_IDEA"])
        on = total(sus, ["TOT_DISCWODIS_SINGOOS", "TOT_DISCWODIS_MULTOOS"], ["SCH_DISCWODIS_SINGOOS", "SCH_DISCWODIS_MULTOOS"])
        ei = total(enr, ["TOT_IDEAENR"], ["SCH_IDEAENR"])
        if ei is None or ei.sum() == 0:
            ei = total(enr, ["SCH_ENR_IDEA"], [])
        et = total(enr, ["TOT_ENR"], [])
        e5 = total(enr, ["TOT_504ENR", "SCH_ENR_504"], [])
        s = pd.DataFrame({"leaid": lid_s, "oi": oi, "on": on}).groupby("leaid").sum()
        e = pd.DataFrame({"leaid": lid_e, "ei": ei, "et": et, "e5": e5 if e5 is not None else 0}).groupby("leaid").sum()
        d = s.join(e, how="inner")
        d["en"] = d.et - d.ei - d.e5
        ri = (100 * d.oi / d.ei).where(d.ei >= 10)
        rn = (100 * d.on / d.en).where(d.en >= 10)
        for lid, a, b in zip(d.index, ri, rn):
            if pd.notna(a) and a <= 100:
                res.setdefault(lid, {}).setdefault("i", {})[y] = round(float(a), 1)
            if pd.notna(b) and b <= 100:
                res.setdefault(lid, {}).setdefault("n", {})[y] = round(float(b), 1)
        print(y, f"{len(d):,} districts; IEP {100 * d.oi.sum() / d.ei.sum():.1f}, no disability {100 * d.on.sum() / d.en.sum():.1f} per 100 (national)")
    (OUT / "district_disc.json").write_text(json.dumps(res, separators=(",", ":")))
    print("Montclair:", res.get("3410560"))


main()
