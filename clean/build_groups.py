"""Students with IEPs and out-of-school suspensions by race and ethnicity, 2023-24 Civil Rights Data Collection, summed from schools to districts.

Same reading rules as build_districts.py: -9 (skipped because the school reported none) is read as 0; -6 and -11 are withheld for
privacy; -5 and -3 are not reported. A district count is kept only when no school withheld or left out that cell; otherwise the
count is marked and no figure is made from it (figures are never estimated).

Output: clean/output/groups.csv.gz, one row per district and group, with three counts and their status:
  enr  students enrolled in the group          (SCH_ENR_<g>)
  iep  students with IEPs in the group         (SCH_IDEAENR_<g>)
  oos  students with IEPs in the group who received one or more out-of-school suspensions
       (SCH_DISCWDIS_SINGOOS_IDEA_<g> + SCH_DISCWDIS_MULTOOS_IDEA_<g>)
"""
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "fetch" / "raw" / "crdc__2023-24-crdc-data.zip"
OUT = ROOT / "clean" / "output" / "groups.csv.gz"
GROUPS = ["HI", "AM", "AS", "HP", "BL", "WH", "TR"]
ITEMS = {"enr": ("SCH/Enrollment.csv", ["SCH_ENR_{g}"]), "iep": ("SCH/Enrollment.csv", ["SCH_IDEAENR_{g}"]),
         "oos": ("SCH/Suspensions.csv", ["SCH_DISCWDIS_SINGOOS_IDEA_{g}", "SCH_DISCWDIS_MULTOOS_IDEA_{g}"])}


def leaid(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(7)


def main():
    z = zipfile.ZipFile(RAW)
    member = lambda short: next(n for n in z.namelist() if n.replace("\\", "/").endswith(short))
    cache, parts = {}, []
    for item, (fname, stems) in ITEMS.items():
        if fname not in cache:
            cache[fname] = pd.read_csv(z.open(member(fname)), dtype=str, encoding="latin-1", keep_default_na=False)
        sch = cache[fname]
        for g in GROUPS:
            total = pd.Series(0.0, index=sch.index)
            bad = pd.Series(False, index=sch.index)
            hid = pd.Series(False, index=sch.index)
            for stem in stems:
                for sex in ("M", "F", "X"):
                    c = f"{stem.format(g=g)}_{sex}"
                    if c not in sch.columns:
                        continue
                    v = pd.to_numeric(sch[c], errors="coerce")
                    if sex != "X":
                        hid |= v.isin([-6, -11])
                        bad |= v.isna() | v.isin([-6, -11, -5, -3]) | ((v < 0) & ~v.isin([-9, -10]))
                    total += v.where(v >= 0, 0).fillna(0)
            d = pd.DataFrame({"leaid": leaid(sch.LEAID), "v": total, "bad": bad, "hid": hid}).groupby("leaid").agg(v=("v", "sum"), bad=("bad", "sum"), hid=("hid", "sum"))
            d["status"] = np.where(d.bad == 0, "ok", np.where(d.hid > 0, "hidden", "not_reported"))
            d["group"], d["item"] = g, item
            parts.append(d.reset_index()[["leaid", "group", "item", "v", "status"]])
    long = pd.concat(parts)
    # combined records (a district that reports for its component districts) add up their parts, as in build_districts.py
    dist = pd.read_csv(ROOT / "clean" / "output" / "districts.csv", dtype={"leaid": str, "part_of": str}, usecols=["leaid", "part_of"])
    dist["leaid"] = leaid(dist.leaid)
    kids = dist.dropna(subset=["part_of"])
    if len(kids):
        kmap = dict(zip(kids.leaid, leaid(kids.part_of)))
        k = long[long.leaid.isin(kmap)].copy()
        k["leaid"] = k.leaid.map(kmap)
        k = k.groupby(["leaid", "group", "item"]).agg(v=("v", "sum"), status=("status", lambda s: "ok" if (s == "ok").all() else ("hidden" if (s == "hidden").any() else "not_reported"))).reset_index()
        long = pd.concat([long[~long.leaid.isin(set(k.leaid))], k])
    long = long[long.leaid.isin(set(dist.leaid))]
    wide = long.pivot_table(index=["leaid", "group"], columns="item", values=["v", "status"], aggfunc="first")
    wide.columns = [f"{b}" if a == "v" else f"{b}_status" for a, b in wide.columns]
    wide = wide.reset_index()
    for c in ("enr", "iep", "oos"):
        wide[c] = wide[c].astype(int)
    wide.to_csv(OUT, index=False)
    print(len(wide), "rows,", wide.leaid.nunique(), "districts;", (wide[["enr_status", "iep_status", "oos_status"]] == "ok").all(axis=1).mean().round(3), "of rows fully reported")


if __name__ == "__main__":
    main()
