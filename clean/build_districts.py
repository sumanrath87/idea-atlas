"""Stage 2: clean and join every source into one record per school district.

Inputs:  fetch/raw/* (original federal files), config/rules.yml,
         config/state_determinations_2026.csv
Outputs: clean/output/districts.csv     one row per district, every measure with its status
         clean/output/zip_lookup.json   ZIP code -> districts that cover it
         clean/reports/quality.md       checks and anything unusual
         clean/reports/spotcheck.md     source figures beside calculated figures, five districts

Status words used for every measure:
  ok            a real figure
  hidden        the agency withheld it to protect privacy (small numbers)
  small_group   fewer than the minimum group (10), so the rate is not shown
  quality       the agency flagged it for data quality
  not_reported  no figure was reported
  none          the group is zero (for example, no students in that group)
  ok_minimum    a real figure, but small parts were withheld, so it is shown as "at least"
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "fetch" / "raw"
OUT = ROOT / "clean" / "output"
REP = ROOT / "clean" / "reports"
RULES = yaml.safe_load((ROOT / "config" / "rules.yml").read_text())
MIN = RULES["minimum_group"]
PER = RULES["rates_per"]
Q: list[str] = []   # quality report lines


def raw(prefix: str) -> Path:
    hits = sorted(RAW.glob(prefix + "*"))
    if not hits:
        raise FileNotFoundError(prefix)
    return hits[0]


def leaid(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(7)


# ---------- reading values with their status ----------

def idea_val(x) -> tuple[float, str]:
    s = "" if pd.isna(x) else str(x).strip()
    if s == "":
        return np.nan, "not_reported"
    if s == "-8":
        return np.nan, "hidden"
    if s == "-9":
        return np.nan, "quality"
    try:
        v = float(s.replace(",", ""))
    except ValueError:
        return np.nan, "not_reported"
    return (v, "ok") if v >= 0 else (np.nan, "not_reported")


def rate(num: float, num_st: str, den: float, den_st: str) -> tuple[float, str]:
    if den_st != "ok":
        return np.nan, den_st
    if den == 0:
        return np.nan, "none"
    if den < MIN:
        return np.nan, "small_group"
    if num_st != "ok":
        return np.nan, num_st
    return round(PER * num / den, 1), "ok"


# ---------- IDEA files (header row comes after a block of notes) ----------

def read_idea(prefix: str) -> pd.DataFrame:
    data = raw(prefix).read_bytes().decode("latin-1").splitlines()
    start = next(i for i, l in enumerate(data) if l.lstrip("﻿ï»¿").startswith("School Year"))
    df = pd.read_csv(io.StringIO("\n".join(data[start:])), dtype=str, keep_default_na=False)
    df = df[df["NCES LEA ID"].str.strip() != ""]
    df["leaid"] = leaid(df["NCES LEA ID"])
    return df


def col(df: pd.DataFrame, *must: str, exclude: tuple[str, ...] = ()) -> str:
    hits = [c for c in df.columns if all(m.lower() in c.lower() for m in must)
            and not any(e.lower() in c.lower() for e in exclude)]
    if len(hits) != 1:
        raise KeyError(f"expected one column with {must}, found {hits}")
    return hits[0]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    used_columns: list[str] = []

    # ---- 1. District list (CCD directory 2024-25) ----
    with zipfile.ZipFile(raw("ccd_directory__ccd_lea_029")) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        d = pd.read_csv(z.open(name), dtype=str, encoding="latin-1", keep_default_na=False)
    d["leaid"] = leaid(d["LEAID"])
    base = d[["leaid", "LEA_NAME", "ST", "STATENAME", "LCITY", "LZIP", "LEA_TYPE_TEXT",
              "CHARTER_LEA_TEXT", "SY_STATUS_TEXT", "GSLO", "GSHI", "WEBSITE"]].rename(columns={
        "LEA_NAME": "name", "ST": "state", "STATENAME": "state_name", "LCITY": "city", "LZIP": "zip",
        "LEA_TYPE_TEXT": "district_type", "CHARTER_LEA_TEXT": "charter", "SY_STATUS_TEXT": "status",
        "GSLO": "grade_low", "GSHI": "grade_high", "WEBSITE": "website"})
    Q.append(f"- District directory: {len(base):,} districts listed; "
             f"{base.leaid.duplicated().sum()} duplicate IDs; status counts: "
             + ", ".join(f"{k} {v:,}" for k, v in base.status.value_counts().items()))

    # ---- 2. Enrollment (CCD membership, district totals only) ----
    with zipfile.ZipFile(raw("ccd_directory__ccd_lea_052")) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        parts, indicators = [], {}
        for ch in pd.read_csv(z.open(name), dtype=str, encoding="latin-1", keep_default_na=False,
                              usecols=["LEAID", "STUDENT_COUNT", "TOTAL_INDICATOR"], chunksize=500_000):
            for k, v in ch.TOTAL_INDICATOR.value_counts().items():
                indicators[k] = indicators.get(k, 0) + v
            parts.append(ch[ch.TOTAL_INDICATOR.str.contains("Education Unit Total", case=False)])
    m = pd.concat(parts)
    m["leaid"] = leaid(m["LEAID"])
    m["enrollment"] = pd.to_numeric(m.STUDENT_COUNT, errors="coerce")
    m = m.groupby("leaid", as_index=False).enrollment.max()
    Q.append("- Enrollment file total types: " + "; ".join(f"{k} ({v:,})" for k, v in indicators.items()))
    base = base.merge(m, on="leaid", how="left")
    base["enrollment_status"] = np.where(base.enrollment.notna() & (base.enrollment >= 0), "ok", "not_reported")

    # ---- 2b. Combined records. NYC is one district in the civil rights, finance, poverty and map
    # files (3620580) but 32 geographic districts in the directory and IDEA files. ----
    combos = RULES.get("combined_districts", [])
    parent_of = {}
    for cmb in combos:
        kids = base[(base.state == cmb["state"]) & base.name.str.contains(cmb["components_match"], case=False, regex=True)]
        for k in kids.leaid:
            parent_of[k] = cmb["leaid"]
        row = {"leaid": cmb["leaid"], "name": cmb["name"], "state": cmb["state"],
               "state_name": kids.state_name.iloc[0], "city": cmb["city"],
               "district_type": f"Combined record of {len(kids)} districts", "charter": "Not a charter district",
               "status": "Open", "enrollment": kids.enrollment.sum(min_count=1), "enrollment_status": "ok"}
        old = base[base.leaid == cmb["leaid"]]
        if len(old):   # the directory lists the central office under the same ID; the combined record replaces it
            for c in ("zip", "website", "grade_low", "grade_high"):
                row[c] = old.iloc[0][c]
            base = base[base.leaid != cmb["leaid"]]
        base = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
        Q.append(f"- Combined record: {cmb['name']} ({cmb['leaid']}) adds up {len(kids)} component districts "
                 f"for enrollment and IDEA counts; other sources report it as one district.")
    base["part_of"] = base.leaid.map(parent_of)

    def add_combined(df: pd.DataFrame, id_cols: int = 6) -> pd.DataFrame:
        """Sum IDEA counts of component districts into a parent row. Cells withheld in any component
        are left out of the sum, so the parent figure for that cell is a minimum."""
        if not parent_of:
            return df
        kids = df[df.leaid.isin(parent_of)]
        new_rows = []
        for parent, grp in kids.groupby(kids.leaid.map(parent_of)):
            r = grp.iloc[0].copy()
            for c in df.columns[id_cols:]:
                if c == "leaid":
                    continue
                vals = [idea_val(v) for v in grp[c]]
                oks = [v for v, st in vals if st == "ok"]
                r[c] = str(int(sum(oks))) if oks else (vals[0][1] == "hidden" and "-8" or "")
            r["leaid"] = parent
            r[df.columns[3]] = "Combined record"
            new_rows.append(r)
        return pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    # ---- 3. IDEA child count 2024-25 ----
    cc = add_combined(read_idea("idea_child_count__"))
    tot_c = col(cc, "Combined Early Childhood and School Age Total")
    sa_c = col(cc, "School Age All Disabilities")
    cats = {"autism": "School Age Autism", "emotional": "School Age Emotional disturbance",
            "intellectual": "School Age Intellectual disability", "learning": "School Age Specific learning disability",
            "speech": "School Age Speech or language impairment", "other_health": "School Age Other health impairment",
            "developmental_delay": "School Age Developmental delay"}
    used_columns += [tot_c, sa_c] + list(cats.values())
    rows = []
    for _, r in cc.iterrows():
        rec = {"leaid": r.leaid}
        rec["idea_count"], rec["idea_count_status"] = idea_val(r[tot_c])
        sa, sa_st = idea_val(r[sa_c])
        rec["idea_school_age"], rec["idea_school_age_status"] = sa, sa_st
        for k, c in cats.items():
            v, st = idea_val(r[col(cc, c)])
            rec[f"cat_{k}"], rec[f"cat_{k}_status"] = rate(v, st, sa, sa_st)
        rows.append(rec)
    cc_t = pd.DataFrame(rows)
    Q.append(f"- IDEA child count 2024-25: {len(cc_t):,} district rows; "
             f"{cc_t.leaid.duplicated().sum()} duplicate IDs; total hidden: "
             f"{(cc_t.idea_count_status == 'hidden').sum():,}; national sum of reported totals "
             f"(combined records not double-counted): "
             f"{cc_t.loc[~cc_t.leaid.isin({c['leaid'] for c in combos}), 'idea_count'].sum():,.0f}")

    # ---- 4. IDEA educational environments 2024-25 (school age) ----
    ev = add_combined(read_idea("idea_environments__"))
    e_all = col(ev, "School Age All Educational Environments")
    e80 = col(ev, "School Age", "80%")
    e40 = col(ev, "School Age", "less than 40%")
    sep = [c for c in ev.columns if c.startswith("School Age") and re.search(
        r"separate school|residential|homebound|hospital", c, re.I)]
    used_columns += [e_all, e80, e40] + sep
    rows = []
    for _, r in ev.iterrows():
        all_v, all_st = idea_val(r[e_all])
        rec = {"leaid": r.leaid}
        rec["env_80plus"], rec["env_80plus_status"] = rate(*idea_val(r[e80]), all_v, all_st)
        rec["env_lt40"], rec["env_lt40_status"] = rate(*idea_val(r[e40]), all_v, all_st)
        vals = [idea_val(r[c]) for c in sep]
        oks = [v for v, st in vals if st == "ok"]
        withheld = any(st in ("hidden", "quality") for _, st in vals)
        if withheld and not oks:
            s_v, s_st = np.nan, next(st for _, st in vals if st in ("hidden", "quality"))
        else:
            s_v, s_st = sum(oks), "ok"
        rec["env_separate"], rec["env_separate_status"] = rate(s_v, s_st, all_v, all_st)
        if withheld and rec["env_separate_status"] == "ok":
            rec["env_separate_status"] = "ok_minimum"   # some small parts withheld: shown as "at least"
        rows.append(rec)
    ev_t = pd.DataFrame(rows)
    Q.append(f"- Educational environments 2024-25: {len(ev_t):,} rows. Separate settings combine: "
             + "; ".join(sep))

    # ---- 5. IDEA exiting 2023-24 ----
    ex = add_combined(read_idea("idea_exiting__"))
    x_tot = col(ex, "Total Exiting School")
    x_reg = col(ex, "Regular High School Diploma")
    x_drop = col(ex, "Dropped Out")
    used_columns += [x_tot, x_reg, x_drop]
    rows = []
    for _, r in ex.iterrows():
        t, t_st = idea_val(r[x_tot])
        rec = {"leaid": r.leaid}
        rec["grad_regular"], rec["grad_regular_status"] = rate(*idea_val(r[x_reg]), t, t_st)
        rec["dropout"], rec["dropout_status"] = rate(*idea_val(r[x_drop]), t, t_st)
        rec["exiting_total"] = t
        rows.append(rec)
    ex_t = pd.DataFrame(rows)

    # ---- 6. Civil rights data 2023-24, summed from schools to districts ----
    groups = {
        "enr_total": ("SCH/Enrollment.csv", ["TOT_ENR"]),
        "enr_idea": ("SCH/Enrollment.csv", ["TOT_IDEAENR"]),
        "enr_504": ("SCH/Enrollment.csv", ["TOT_504ENR"]),
        "oos_idea": ("SCH/Suspensions.csv", ["TOT_DISCWDIS_SINGOOS_IDEA", "TOT_DISCWDIS_MULTOOS_IDEA"]),
        "oos_nodis": ("SCH/Suspensions.csv", ["TOT_DISCWODIS_SINGOOS", "TOT_DISCWODIS_MULTOOS"]),
        "oos_504": ("SCH/Suspensions.csv", ["SCH_DISCWDIS_SINGOOS_504", "SCH_DISCWDIS_MULTOOS_504"]),
        "exp_idea": ("SCH/Expulsions.csv", ["TOT_DISCWDIS_EXPWE_IDEA", "TOT_DISCWDIS_EXPWOE_IDEA"]),
        "rs_phys_idea": ("SCH/Restraints and Seclusion.csv", ["TOT_RS_IDEA_PHYS"]),
        "rs_mech_idea": ("SCH/Restraints and Seclusion.csv", ["TOT_RS_IDEA_MECH"]),
        "rs_secl_idea": ("SCH/Restraints and Seclusion.csv", ["TOT_RS_IDEA_SECL"]),
        "ref_idea": ("SCH/Referrals and Arrests.csv", ["TOT_DISCWDIS_REF_IDEA"]),
        "arr_idea": ("SCH/Referrals and Arrests.csv", ["TOT_DISCWDIS_ARR_IDEA"]),
    }
    crdc = {}
    with zipfile.ZipFile(raw("crdc__")) as z:
        names = {n.split("/", 1)[-1] if n.count("/") > 1 else n: n for n in z.namelist()}

        def member(short: str) -> str:
            return next(n for n in z.namelist() if n.replace("\\", "/").endswith(short))

        cache: dict[str, pd.DataFrame] = {}
        for key, (fname, stems) in groups.items():
            if fname not in cache:
                cache[fname] = pd.read_csv(z.open(member(fname)), dtype=str, encoding="latin-1",
                                           keep_default_na=False)
            sch = cache[fname]
            # Civil rights codes (2023-24): -9 = skipped because the school reported none, read as 0;
            # -6 and -11 = withheld for privacy; -5 and -3 = not reported; -10 = withheld category (nonbinary).
            total = pd.Series(0.0, index=sch.index)
            hidden = pd.Series(False, index=sch.index)
            missing = pd.Series(False, index=sch.index)
            for stem in stems:
                for sex in ("M", "F", "X"):
                    c = f"{stem}_{sex}"
                    if c not in sch.columns:
                        continue
                    used_columns.append(c)
                    v = pd.to_numeric(sch[c], errors="coerce")
                    if sex == "X":
                        total += v.where(v >= 0, 0).fillna(0)
                        continue
                    hidden |= v.isin([-6, -11])
                    missing |= v.isna() | v.isin([-5, -3]) | ((v < 0) & ~v.isin([-9, -6, -11, -10]))
                    total += v.where(v >= 0, 0).fillna(0)
            g = pd.DataFrame({"leaid": leaid(sch.LEAID), "v": total, "hid": hidden, "mis": missing})
            agg = g.groupby("leaid").agg(v=("v", "sum"), schools=("v", "size"), hid=("hid", "sum"), mis=("mis", "sum"))
            none_ok = (agg.hid + agg.mis) >= agg.schools
            agg[key] = np.where(none_ok, np.nan, agg.v)
            agg[key + "_status"] = np.where(none_ok, np.where(agg.hid > 0, "hidden", "not_reported"),
                                            np.where((agg.hid + agg.mis) > 0, "ok_partial", "ok"))
            crdc[key] = agg[[key, key + "_status"]]
            if key == "enr_total":
                crdc["schools"] = agg[["schools"]]
    cr = pd.concat(crdc.values(), axis=1).reset_index()

    def crdc_rate(numk: str, denk: str) -> tuple[pd.Series, pd.Series]:
        vals, sts = [], []
        for n, ns, d_, ds in zip(cr[numk], cr[numk + "_status"], cr[denk], cr[denk + "_status"]):
            v, st = rate(n, "ok" if ns.startswith("ok") else ns, d_, "ok" if str(ds).startswith("ok") else ds)
            vals.append(v)
            sts.append(st)
        return pd.Series(vals), pd.Series(sts)

    cr["enr_nodis"] = cr.enr_total - cr.enr_idea.fillna(0) - cr.enr_504.fillna(0)
    cr["enr_nodis_status"] = cr.enr_total_status
    out_cr = pd.DataFrame({"leaid": cr.leaid, "crdc_schools": cr.schools,
                           "crdc_enr_idea": cr.enr_idea, "crdc_enr_504": cr.enr_504})
    for name_, (n_, d_) in {
        "pct_504": ("enr_504", "enr_total"),
        "oos_idea": ("oos_idea", "enr_idea"), "oos_nodis": ("oos_nodis", "enr_nodis"),
        "oos_504": ("oos_504", "enr_504"), "expulsion_idea": ("exp_idea", "enr_idea"),
        "restraint_physical_idea": ("rs_phys_idea", "enr_idea"),
        "restraint_mechanical_idea": ("rs_mech_idea", "enr_idea"),
        "seclusion_idea": ("rs_secl_idea", "enr_idea"),
        "referral_idea": ("ref_idea", "enr_idea"), "arrest_idea": ("arr_idea", "enr_idea"),
    }.items():
        out_cr[name_], out_cr[name_ + "_status"] = crdc_rate(n_, d_)
    out_cr["crdc_partial"] = (cr.filter(like="_status") == "ok_partial").any(axis=1)
    Q.append(f"- Civil rights data 2023-24: {len(out_cr):,} districts from "
             f"{int(cr.schools.sum()):,} schools. A count of -9 (skipped because the school reported none) "
             f"is read as zero. Districts where at least one school withheld or did not report an item "
             f"(figure shown as a minimum): {int(out_cr.crdc_partial.sum()):,}")

    # ---- 7. District finance FY2024 (Census, dollars in thousands) ----
    f = pd.read_excel(raw("f33__elsec24.xlsx"), sheet_name="elsec24", dtype=str)
    f["leaid"] = leaid(f["NCESID"])
    for c in ("V33", "TCURELSC", "C15", "TOTALEXP"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    used_columns += ["NCESID", "V33 (fall enrollment)", "TCURELSC (current spending, $000)",
                     "C15 (federal IDEA revenue through state, $000)"]
    fin = pd.DataFrame({"leaid": f.leaid})
    fin["spend_per_pupil"] = np.where(f.V33 >= MIN, (f.TCURELSC * 1000 / f.V33).round(0), np.nan)
    fin["spend_per_pupil_status"] = np.where(fin.spend_per_pupil.notna(), "ok",
                                             np.where(f.V33 < MIN, "small_group", "not_reported"))
    fin["idea_federal_revenue"] = (f.C15 * 1000).round(0)
    fin["idea_federal_revenue_status"] = np.where(f.C15.notna(), "ok", "not_reported")
    fin = fin.drop_duplicates("leaid")
    Q.append(f"- Finance FY2024: {len(fin):,} districts; federal IDEA revenue total "
             f"${fin.idea_federal_revenue.sum() / 1e9:,.2f} billion")

    # ---- 8. Child poverty 2024 (SAIPE, fixed-width text, one file per state) ----
    rows = []
    for p in sorted(RAW.glob("saipe__sd24-*.txt")):
        for line in p.read_text(encoding="latin-1").splitlines():
            t = line.split()
            if len(t) < 8 or not t[0].isdigit():
                continue
            pop, kids, poor = (int(x) for x in t[-5:-2])
            rows.append({"leaid": t[0] + t[1], "children_5_17": kids, "children_poor": poor})
    sa = pd.DataFrame(rows).drop_duplicates("leaid")
    sa["child_poverty"], sa["child_poverty_status"] = zip(*[
        rate(p_, "ok", k_, "ok") for p_, k_ in zip(sa.children_poor, sa.children_5_17)])
    Q.append(f"- Child poverty 2024: {len(sa):,} districts from {len(list(RAW.glob('saipe__sd24-*.txt')))} state files")

    # ---- 9. State determinations 2026 ----
    det = pd.read_csv(ROOT / "config" / "state_determinations_2026.csv", dtype=str)
    det["state_name"] = det.entity.str.upper()
    base = base.merge(det[["state_name", "determination_2026"]], on="state_name", how="left")

    # ---- 10. Join everything ----
    out = base
    for part in (cc_t, ev_t, ex_t, out_cr, fin, sa[["leaid", "child_poverty", "child_poverty_status"]]):
        out = out.merge(part, on="leaid", how="left")
    out["id_rate"], out["id_rate_status"] = zip(*[
        rate(n, ns if isinstance(ns, str) else "not_reported", d_, ds)
        for n, ns, d_, ds in zip(out.idea_count, out.idea_count_status, out.enrollment, out.enrollment_status)])
    out["idea_federal_per_student"] = np.where(
        (out.idea_count_status == "ok") & (out.idea_count >= MIN) & (out.idea_federal_revenue_status == "ok"),
        (out.idea_federal_revenue / out.idea_count).round(0), np.nan)
    out["idea_federal_per_student_status"] = np.where(
        out.idea_federal_per_student.notna(), "ok",
        np.where(out.idea_count_status.isin(["hidden", "quality"]), out.idea_count_status,
                 np.where(out.idea_count < MIN, "small_group", "not_reported")))
    # Flag districts whose civil rights IEP count is far from their IDEA count. Their discipline
    # rates use the civil rights count, so the site shows a note asking readers to check with the district.
    out["crdc_count_check"] = (out.crdc_enr_idea.notna() & out.idea_count.notna() & (out.idea_count >= 50)
                               & ((out.crdc_enr_idea - out.idea_count).abs() > 0.5 * out.idea_count))
    status_cols = [c for c in out.columns if c.endswith("_status")]
    out[status_cols] = out[status_cols].fillna("not_reported")
    out.to_csv(OUT / "districts.csv", index=False)

    # ---- 11. ZIP lookup (Census ZIP code areas to districts, 2025) ----
    with zipfile.ZipFile(raw("edge_zcta__")) as z:
        name = next(n for n in z.namelist() if n.lower().endswith("zcta5ce20.xlsx"))
        g = pd.read_excel(z.open(name), dtype={"LEAID": str, "ZCTA5CE20": str})
    g["leaid"] = leaid(g.LEAID)
    g["LANDAREA"] = pd.to_numeric(g.LANDAREA, errors="coerce").fillna(0)
    g = g[g.ZCTA5CE20.str.fullmatch(r"\d{5}") & (g.ZCTA5CE20 != "00000")]
    g["share"] = g.LANDAREA / g.groupby("ZCTA5CE20").LANDAREA.transform("sum").replace(0, np.nan)
    zl = {}
    for z5, grp in g.sort_values("share", ascending=False).groupby("ZCTA5CE20", sort=True):
        zl[z5] = [[r.leaid, round(float(r.share), 3) if pd.notna(r.share) else None] for r in grp.itertuples()]
    (OUT / "zip_lookup.json").write_text(json.dumps(zl, separators=(",", ":")))
    multi = sum(1 for v in zl.values() if len(v) > 1)
    Q.append(f"- ZIP lookup: {len(zl):,} ZIP code areas; {multi:,} cover more than one district "
             f"(the site will list all of them, largest share first)")

    # ---- 12. Boundaries: do the map shapes match the district list? ----
    try:
        import pyogrio
        with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(raw("edge_boundaries__")) as z:
            z.extractall(td)
            shp = next(Path(td).rglob("*.shp"))
            b = pyogrio.read_dataframe(shp, read_geometry=False)
        idcol = next(c for c in b.columns if c.upper() in ("GEOID", "LEAID"))
        shapes = set(leaid(b[idcol]))
        Q.append(f"- Map shapes 2024-25: {len(shapes):,} districts with a boundary; "
                 f"{len(set(out.leaid) & shapes):,} of {len(out):,} listed districts have one "
                 f"(charter and specialty districts usually do not)")
    except Exception as e:  # noqa: BLE001
        Q.append(f"- Map shapes: could not check ({e})")

    # ---- 13. Quality checks ----
    open_ = out[out.status.str.contains("Open|Added|New|Reopened|Changed", case=False, na=False)]
    Q.append("")
    Q.append("## Match rates (open districts)")
    Q.append(f"Open or active districts: {len(open_):,}")
    for label, c in [("IDEA child count", "idea_count_status"), ("Environments", "env_80plus_status"),
                     ("Exiting", "grad_regular_status"), ("Civil rights", "oos_idea_status"),
                     ("Finance", "spend_per_pupil_status"), ("Child poverty", "child_poverty_status")]:
        vc = open_[c].value_counts()
        Q.append(f"- {label}: " + ", ".join(f"{k} {v:,}" for k, v in vc.items()))
    Q.append("")
    Q.append("## Unusual values to look at")
    checks = {
        "Identification rate above 50 per 100 (often schools for the deaf or blind, or online schools)": out.id_rate > 50,
        "Suspension rate for students with IEPs above 100 (students counted in two suspension types)": out.oos_idea > 100,
        "Civil rights IEP count differs from IDEA count by more than half (different school years or reporting)":
            (out.crdc_enr_idea.notna() & out.idea_count.notna() & (out.idea_count >= 50)
             & ((out.crdc_enr_idea - out.idea_count).abs() > 0.5 * out.idea_count)),
        "Spending per pupil above $60,000": out.spend_per_pupil > 60000,
        "Graduation share of 100 with 30 or more leavers": (out.grad_regular == 100) & (out.exiting_total >= 30),
    }
    for label, mask in checks.items():
        n = int(mask.fillna(False).sum())
        ex_ = out.loc[mask.fillna(False), ["name", "state"]].head(5)
        Q.append(f"- {label}: {n:,}" + (" (e.g. " + "; ".join(f"{a}, {b}" for a, b in ex_.values) + ")" if n else ""))
    Q.append("")
    Q.append("## Columns used from each source")
    Q.append(", ".join(f"`{c}`" for c in dict.fromkeys(used_columns)))

    (REP / "quality.md").write_text("# Quality report\n\n" + "\n".join(Q) + "\n")

    # ---- 14. Spot-check: source figures beside calculated figures ----
    S = ["# Spot-check: five districts", "",
         "Each figure below is shown as it appears in the original file, then as IDEA Atlas calculates it.", ""]
    for pick in RULES["spot_check"]:
        hit = out[(out.state == pick["state"]) & out.name.str.contains(pick["name"], case=False, regex=False)]
        hit = hit.sort_values("enrollment", ascending=False).head(1)
        if hit.empty:
            S.append(f"## {pick['name']}, {pick['state']}: not found\n")
            continue
        r = hit.iloc[0]
        lid = r.leaid
        S.append(f"## {r['name']}, {r.state} (NCES ID {lid})")
        S.append("")
        src_cc = cc[cc.leaid == lid]
        src_ev = ev[ev.leaid == lid]
        src_ex = ex[ex.leaid == lid]
        src_f = f[f.leaid == lid]
        src_s = sa[sa.leaid == lid]
        S.append("| Measure | In the original file | Calculated |")
        S.append("|---|---|---|")
        S.append(f"| Enrollment 2024-25 | CCD total: {r.enrollment:,.0f} | {r.enrollment:,.0f} |" if pd.notna(r.enrollment) else "| Enrollment | not found | |")
        if len(src_cc):
            S.append(f"| Students with IEPs, ages 3-21 | {src_cc.iloc[0][tot_c]} | {r.idea_count:,.0f} ({r.idea_count_status}) |"
                     if pd.notna(r.idea_count) else f"| Students with IEPs | {src_cc.iloc[0][tot_c]} | {r.idea_count_status} |")
            S.append(f"| Students with IEPs per 100 enrolled | {src_cc.iloc[0][tot_c]} ÷ {r.enrollment:,.0f} | {r.id_rate} ({r.id_rate_status}) |")
            S.append(f"| Specific learning disability, share of school-age | {src_cc.iloc[0][col(cc, cats['learning'])]} of {src_cc.iloc[0][sa_c]} | {r.cat_learning} ({r.cat_learning_status}) |")
        if len(src_ev):
            S.append(f"| In general class 80%+ of the day | {src_ev.iloc[0][e80]} of {src_ev.iloc[0][e_all]} | {r.env_80plus} ({r.env_80plus_status}) |")
            S.append(f"| Separate school or facility | {' + '.join(src_ev.iloc[0][c] for c in sep)} of {src_ev.iloc[0][e_all]} | {r.env_separate} ({r.env_separate_status}) |")
        if len(src_ex):
            S.append(f"| Regular diploma, share of leavers (2023-24) | {src_ex.iloc[0][x_reg]} of {src_ex.iloc[0][x_tot]} | {r.grad_regular} ({r.grad_regular_status}) |")
        if pd.notna(r.get("crdc_enr_idea")):
            crow = cr[cr.leaid == lid].iloc[0]
            S.append(f"| Out-of-school suspension, students with IEPs (2023-24) | {crow.oos_idea:,.0f} of {crow.enr_idea:,.0f} | {r.oos_idea} ({r.oos_idea_status}) |")
            S.append(f"| Out-of-school suspension, students without disabilities | {crow.oos_nodis:,.0f} of {crow.enr_nodis:,.0f} | {r.oos_nodis} ({r.oos_nodis_status}) |")
            S.append(f"| Section 504 students per 100 enrolled | {crow.enr_504:,.0f} of {crow.enr_total:,.0f} | {r.pct_504} ({r.pct_504_status}) |")
            S.append(f"| Physical restraint, students with IEPs | {crow.rs_phys_idea:,.0f} of {crow.enr_idea:,.0f} | {r.restraint_physical_idea} ({r.restraint_physical_idea_status}) |")
            S.append(f"| Referred to law enforcement, students with IEPs | {crow.ref_idea:,.0f} of {crow.enr_idea:,.0f} | {r.referral_idea} ({r.referral_idea_status}) |")
        if len(src_f):
            fr = src_f.iloc[0]
            S.append(f"| Current spending per pupil (FY2024) | ${fr.TCURELSC:,.0f} thousand ÷ {fr.V33:,.0f} students | ${r.spend_per_pupil:,.0f} |")
            S.append(f"| Federal IDEA money (FY2024) | ${fr.C15:,.0f} thousand | ${r.idea_federal_revenue:,.0f} |")
        if len(src_s):
            sr = src_s.iloc[0]
            S.append(f"| Children 5-17 in poverty (2024) | {sr.children_poor:,} of {sr.children_5_17:,} | {r.child_poverty} |")
        S.append(f"| State IDEA rating (2026) | {r.state_name.title()} | {r.determination_2026} |")
        S.append("")
    (REP / "spotcheck.md").write_text("\n".join(S) + "\n")
    print("\n".join(Q))
    print("\n".join(S))
    return 0


if __name__ == "__main__":
    sys.exit(main())
