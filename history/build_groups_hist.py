"""Students with IEPs and out-of-school suspensions by race and ethnicity over time, Civil Rights Data Collection, summed from schools to districts.
Years: 2013-14, 2015-16, 2017-18, 2020-21, 2021-22 (from the raw files) and 2023-24 (from clean/output/groups.csv.gz).
Counts per district, group, and year: students enrolled, students with IEPs, and students with IEPs with one or more out-of-school suspensions.
A district-year is left out when its total share of students with IEPs is more than 35% away from the atlas's screened IEP share
for that year (district_trends.json.gz), which catches years where schools are missing or misreported. As in build_discipline.py, a negative code (not applicable, suppressed, not reported) is read as 0 for a school; the 2023-24 counts keep the
atlas's stricter rule (a count with any withheld school is left out).

Writes build/history/groups/<state FIPS>.json: {leaid: {fall_year: [[group, enrolled, with IEPs, with IEPs suspended], ...]}}.
The report assistant loads one state's file only when a report needs it."""
import gzip
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "raw/crdc")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "history" / "groups"
G = ["AM", "AS", "BL", "HI", "HP", "TR", "WH"]
KEEP = re.compile(r"^(LEAID|SCH_ENR_(AM|AS|BL|HI|HP|TR|WH)_[MFX]|SCH_IDEAENR_(AM|AS|BL|HI|HP|TR|WH)_[MFX]|SCH_DISCWDIS_(SING|MULT)OOS_IDEA_(AM|AS|BL|HI|HP|TR|WH)_[MFX])$")


def leaid(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(7)


def frames(year):
    z = zipfile.ZipFile(RAW / f"{year}-{str(year + 1)[2:]}.zip")
    names = z.namelist()
    if year == 2013:
        rd = lambda end: pd.read_excel(io.BytesIO(z.read(next(n for n in names if n.endswith(end)))), dtype=str)
        return [rd("03 Enrollment.xlsx"), rd("11-2 Suspensions (required elements).xlsx")]
    if year == 2015:
        files = [next(n for n in names if n.endswith("CRDC 2015-16 School Data.csv"))]
    else:
        files = [next(n for n in names if re.search(rf"(SCH|School)/(CRDC/CSV/)?{f}\.csv$", n)) for f in ("Enrollment", "Suspensions")]
    out = []
    for n in files:
        head = pd.read_csv(z.open(n), nrows=0, encoding="latin-1").columns
        out.append(pd.read_csv(z.open(n), dtype=str, encoding="latin-1", usecols=[c for c in head if KEEP.match(c)]))
    return out


def counts(df, stems):
    res = {}
    for g in G:
        cols = [f"{s}_{g}_{x}" for s in stems for x in ("M", "F", "X") if f"{s}_{g}_{x}" in df.columns]
        if cols:
            v = df[cols].apply(pd.to_numeric, errors="coerce")
            res[g] = v.where(v > 0, 0).sum(axis=1)
    return pd.DataFrame(res).assign(leaid=leaid(df.LEAID)).groupby("leaid").sum() if res else None


def main():
    dist = pd.read_csv(ROOT / "clean" / "output" / "districts.csv", dtype=str, usecols=["leaid", "part_of"])
    dist["leaid"] = leaid(dist.leaid)
    keep = set(dist.leaid)
    kmap = {k: leaid(pd.Series([p])).iloc[0] for k, p in zip(dist.leaid, dist.part_of) if isinstance(p, str)}
    trend = json.loads(gzip.open(ROOT / "build" / "history" / "district_trends.json.gz").read())
    res = {}
    for y in (2013, 2015, 2017, 2020, 2021):
        fr = frames(y)
        enr_df, sus_df = fr[0], fr[-1]
        e = counts(enr_df, ["SCH_ENR"])
        i = counts(enr_df, ["SCH_IDEAENR"])
        o = counts(sus_df, ["SCH_DISCWDIS_SINGOOS_IDEA", "SCH_DISCWDIS_MULTOOS_IDEA"])
        if e is None or i is None or o is None:
            print(y, "missing columns"); continue
        tabs = []
        for t in (e, i, o):                      # combined records add up their component districts
            t = t.rename(index=lambda x: kmap.get(x, x)).groupby(level=0).sum()
            tabs.append(t)
        e, i, o = tabs
        ids = sorted(set(e.index) & set(i.index) & keep)
        o = o.reindex(ids).fillna(0)
        n = dropped = 0
        for lid in ids:
            ref = trend.get(lid, {}).get("i", {}).get(str(y))      # the atlas's screened IEP share for that year
            te, ti = float(e.loc[lid].sum()), float(i.loc[lid].sum())
            if ref and te and abs(100 * ti / te - ref) > 0.35 * ref:
                dropped += 1
                continue
            rows = [[g, int(e.at[lid, g]), int(i.at[lid, g]), int(o.at[lid, g])] for g in G if g in e.columns and e.at[lid, g] > 0]
            if rows:
                res.setdefault(lid, {})[y] = rows
                n += 1
        tot = lambda t: int(t.reindex(ids).sum().sum())
        print(y, f"{n:,} districts ({dropped:,} left out: total far from the screened IEP share); students with IEPs {tot(i):,}; suspended {tot(o):,}")
    g23 = pd.read_csv(ROOT / "clean" / "output" / "groups.csv.gz", dtype={"leaid": str})
    g23["o"] = g23.group.map(G.index)
    for lid, g in g23.sort_values(["leaid", "o"]).groupby("leaid"):
        rows = [[x.group, *(int(getattr(x, c)) if getattr(x, c + "_status") == "ok" else None for c in ("enr", "iep", "oos"))] for x in g.itertuples() if x.enr_status != "ok" or x.enr > 0]
        if rows:
            res.setdefault(lid, {})[2023] = rows
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"):
        f.unlink()
    by_state = {}
    for lid, v in res.items():
        by_state.setdefault(lid[:2], {})[lid] = v
    size = 0
    for st, v in by_state.items():
        p = OUT / f"{st}.json"
        p.write_text(json.dumps(v, separators=(",", ":")))
        size += p.stat().st_size
    print(f"{len(by_state)} state files, {size / 1e6:.1f} MB; Montclair:", {k: v for k, v in res.get("3410560", {}).items()})


main()
