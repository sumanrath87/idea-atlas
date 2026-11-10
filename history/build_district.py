"""District trend lines for IDEA Atlas.

Students with IEPs per 100 enrolled, by district and year, from the Common Core of Data:
  1991-92 to 2006-07  fixed-width agency universe files (layouts give field positions)
  2007-08 to 2013-14  tab-separated agency universe files (MEMBERyy, SPECEDyy)
  2014-15 to 2017-18  separate membership (052) and IDEA count (002089 / 2_89) files
Writes history/output/district_iep.json: {leaid: {fall_year: rate}} for rates that pass basic checks.
"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "raw/ccd")
OUT = Path(__file__).resolve().parent / "output"


def read_zip_text(z: Path, prefer=(".txt", ".dat", ".csv")) -> tuple[str, bytes]:
    with zipfile.ZipFile(z) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(prefer)]
        n = names[0]
        try:
            return n, zf.read(n)
        except NotImplementedError:            # 1990s files use an old compression; the system unzip reads it
            import subprocess
            return n, subprocess.run(["unzip", "-p", str(z), n], capture_output=True, check=True).stdout


def layout_positions(lay: Path, yy: str) -> dict[str, tuple[int, int]]:
    txt = lay.read_text(encoding="latin-1")
    pos = {}
    for name in ("LEAID", f"MEMBER{yy}", f"SPECED{yy}"):
        m = re.search(rf"^\s*{name}\s+[^\n]*?(\d{{1,4}})\s*-\s*(\d{{1,4}})", txt, re.M) or \
            re.search(rf"^\s*{name}\s+(\d{{4}})\s+(\d{{4}})", txt, re.M)
        if m:
            pos[name] = (int(m.group(1)), int(m.group(2)))
    return pos


def fixed(z: Path, lay: Path, yy: str):
    pos = layout_positions(lay, yy)
    if len(pos) < 3:
        return None
    _, data = read_zip_text(z)
    rows = []
    for line in data.decode("latin-1").splitlines():
        g = lambda k: line[pos[k][0] - 1:pos[k][1]].strip()
        rows.append((g("LEAID"), g(f"MEMBER{yy}"), g(f"SPECED{yy}")))
    return pd.DataFrame(rows, columns=["leaid", "member", "speced"])


def tabbed(z: Path, yy: str):
    _, data = read_zip_text(z)
    df = pd.read_csv(io.BytesIO(data), sep="\t", dtype=str, encoding="latin-1", low_memory=False)
    m = next((c for c in df.columns if c.upper() in (f"MEMBER{yy}", "MEMBER")), None)
    s = next((c for c in df.columns if c.upper() in (f"SPECED{yy}", "SPECED")), None)
    if not (m and s):
        return None
    return df[["LEAID", m, s]].set_axis(["leaid", "member", "speced"], axis=1)


def modern(year: int):
    tag = f"{str(year)[2:]}{str(year + 1)[2:]}"
    mem = next(iter(RAW.glob(f"ccd_lea_052_{tag}_*.zip")), None)
    idea = next(iter(RAW.glob(f"ccd_lea_002089_{tag}_*.zip")), None) or next(iter(RAW.glob(f"ccd_lea_2_89_{tag}_*.zip")), None)
    if not (mem and idea):
        return None
    n, b = read_zip_text(mem, (".csv", ".txt"))
    md = pd.read_csv(io.BytesIO(b), sep="\t" if n.endswith(".txt") else ",", dtype=str, encoding="latin-1", low_memory=False)
    md.columns = [c.upper() for c in md.columns]
    # long files list counts by grade/race/sex; keep the district total
    if "TOTAL_INDICATOR" in md.columns:
        md = md[md.TOTAL_INDICATOR.str.contains("Education Unit Total", na=False)]
        mem_s = md.groupby("LEAID").STUDENT_COUNT.apply(lambda x: pd.to_numeric(x, errors="coerce").max())
    else:
        col = next(c for c in md.columns if c in ("MEMBER", "TOTAL") or c.startswith("MEMBER"))
        mem_s = md.set_index("LEAID")[col]
    n, b = read_zip_text(idea, (".csv", ".txt"))
    idd = pd.read_csv(io.BytesIO(b), sep="\t" if n.endswith(".txt") else ",", dtype=str, encoding="latin-1", low_memory=False)
    idd.columns = [c.upper() for c in idd.columns]
    sp = idd.set_index("LEAID")[next(c for c in idd.columns if "IDEA" in c and "COUNT" in c or c == "SPECED")]
    out = pd.DataFrame({"member": mem_s}).join(pd.DataFrame({"speced": sp}), how="inner").reset_index()
    return out.rename(columns={"index": "leaid", "LEAID": "leaid"})


OSEP = Path("raw/osep")


def membership(year: int) -> pd.Series:
    """District totals from the CCD membership file, read in pieces (the 2022-23 file is very large)."""
    tag = f"{str(year)[2:]}{str(year + 1)[2:]}"
    z = next(iter(RAW.glob(f"ccd_lea_052_{tag}_*.zip")))
    with zipfile.ZipFile(z) as zf:
        n = [x for x in zf.namelist() if x.lower().endswith(".csv")][0]
        parts = []
        for ch in pd.read_csv(zf.open(n), dtype=str, usecols=["LEAID", "STUDENT_COUNT", "TOTAL_INDICATOR"], chunksize=2_000_000, encoding="latin-1"):
            ch = ch[ch.TOTAL_INDICATOR.str.contains("Education Unit Total", na=False)]
            parts.append(ch)
    m = pd.concat(parts)
    return m.groupby("LEAID").STUDENT_COUNT.apply(lambda x: pd.to_numeric(x, errors="coerce").max())


def osep(year: int):
    f = next(iter(OSEP.glob(f"*lea{year}-{str(year + 1)[2:]}.csv")))
    lines = f.read_bytes().decode("latin-1").splitlines()
    start = next(i for i, l in enumerate(lines) if l.lstrip("\ufeffï»¿").startswith("School Year"))
    d = pd.read_csv(io.StringIO("\n".join(lines[start:])), dtype=str, keep_default_na=False)
    d = d[d["NCES LEA ID"].str.strip() != ""]
    sp = pd.Series(pd.to_numeric(d["Combined Early Childhood and School Age Total"], errors="coerce").values,
                   index=d["NCES LEA ID"].str.strip().str.zfill(7))
    mem = membership(year)
    sp.index.name = None
    mem.index.name = None
    out = pd.DataFrame({"speced": sp}).join(pd.DataFrame({"member": mem}), how="inner").reset_index()
    return out.rename(columns={"index": "leaid"})


def files():
    """(fall year, kind, path, layout, two-digit suffix)"""
    out = []
    for y in range(1991, 1998):
        z = RAW / f"pau{str(y)[2:]}data.zip"
        if not z.exists():
            z = RAW / f"pau{str(y)[2:]}datr.zip"
        out.append((y, "fixed", z, RAW / f"pau{str(y)[2:]}lay.txt", str(y)[2:]))
    for y, z, lay in [(1998, "ag981c_dat.zip", "pau98lay.txt"), (1999, "ag991b_dat.zip", "pau99lay.txt"), (2000, "ag001a_dat.zip", "pau00lay.txt"),
                      (2001, "ag011a_dat.zip", "pau01lay.txt"), (2002, "ag021a_dat.zip", "pau021alay.txt"), (2003, "ag031b_dat.zip", "pau031blay.txt"),
                      (2004, "ag041c_dat.zip", "pau041clay.txt"), (2005, "ag051a_dat.zip", "pau051alay.txt"), (2006, "ag061c_dat.zip", "pau061clay.txt")]:
        out.append((y, "fixed", RAW / z, RAW / lay, str(y)[2:]))
    for y, z in [(2007, "ag071b_txt.zip"), (2008, "ag081a_txt.zip"), (2009, "ag092a_txt.zip"), (2010, "ag102a_txt.zip"),
                 (2011, "ag111a_txt.zip"), (2012, "ag121a_supp_txt.zip"), (2013, "ag131a_supp_txt.zip")]:
        out.append((y, "tab", RAW / z, None, str(y)[2:]))
    for y in range(2014, 2020):
        out.append((y, "modern", None, None, ""))
    for y in range(2020, 2024):
        out.append((y, "osep", None, None, ""))
    return out


FIPS_NAME = {"01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas", "06": "California", "08": "Colorado", "09": "Connecticut",
             "10": "Delaware", "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii", "16": "Idaho", "17": "Illinois",
             "18": "Indiana", "19": "Iowa", "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine", "24": "Maryland",
             "25": "Massachusetts", "26": "Michigan", "27": "Minnesota", "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
             "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico", "36": "New York", "37": "North Carolina",
             "38": "North Dakota", "39": "Ohio", "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina",
             "46": "South Dakota", "47": "Tennessee", "48": "Texas", "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
             "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming"}


def official(st: str, y: int):
    """The state's official share served (Digest of Education Statistics), straight or interpolated between published years."""
    states = json.loads((Path(__file__).resolve().parent / "output" / "states.json").read_text())
    d = {int(k): v["pct"] for k, v in states.get(FIPS_NAME.get(st, ""), {}).items() if v.get("pct")}
    if not d:
        return None
    if y in d:
        return d[y]
    lo = max((k for k in d if k < y), default=None)
    hi = min((k for k in d if k > y), default=None)
    if lo is None or hi is None:
        return d[lo if lo is not None else hi] if (lo or hi) and abs((lo or hi) - y) <= 2 else None
    return d[lo] + (d[hi] - d[lo]) * (y - lo) / (hi - lo)


def screen(series, sums):
    """1) Leave out a state's year when its districts' combined rate is far (over 35%) from the state's official share served
    that year, a sign the state reported IEP counts differently (for example, at a regional or state agency).
    2) Leave out a single-year spike that both neighbouring years contradict."""
    bad = set()
    for (st, y), (sp, mem) in sums.items():
        ref = official(st, y)
        if ref and mem and abs(100 * sp / mem - ref) / ref > 0.35:
            bad.add((st, y))
    out, spikes = {}, 0
    for lid, ys in series.items():
        keep = {y: v for y, v in ys.items() if (lid[:2], y) not in bad}
        yrs = sorted(keep)
        for i in range(1, len(yrs) - 1):
            a, b, c = keep[yrs[i - 1]], keep[yrs[i]], keep[yrs[i + 1]]
            if a and c and abs(a - c) / max(a, c) < 0.2 and abs(b - (a + c) / 2) / ((a + c) / 2) > 0.35:
                keep[yrs[i]] = None
                spikes += 1
        keep = {y: v for y, v in keep.items() if v is not None}
        if len(keep) >= 2:
            out[lid] = keep
    return out, {"state_years": len(bad), "spikes": spikes, "which": {f"{st}-{y}" for st, y in bad}}


def main():
    OUT.mkdir(exist_ok=True)
    series: dict[str, dict[int, float]] = {}
    sums: dict = {}
    report = []
    for y, kind, z, lay, yy in files():
        try:
            df = fixed(z, lay, yy) if kind == "fixed" else tabbed(z, yy) if kind == "tab" else osep(y) if kind == "osep" else modern(y)
        except Exception as e:  # noqa: BLE001
            report.append(f"{y}: failed {e}")
            continue
        if df is None:
            report.append(f"{y}: fields not found")
            continue
        df["member"] = pd.to_numeric(df.member, errors="coerce")
        df["speced"] = pd.to_numeric(df.speced, errors="coerce")
        df["leaid"] = df.leaid.astype(str).str.strip().str.zfill(7)
        ok = (df.member >= 10) & (df.speced >= 0) & (df.speced <= df.member * 0.6)
        good = df[ok]
        for lid, m, s in zip(good.leaid, good.member, good.speced):
            series.setdefault(lid, {})[y] = round(100 * s / m, 1)
        g2 = good.assign(st=good.leaid.str[:2]).groupby("st")[["speced", "member"]].sum()
        for st, row in g2.iterrows():
            sums[(st, y)] = (row.speced, row.member)
        nat = 100 * good.speced.sum() / good.member.sum() if len(good) else 0
        report.append(f"{y}: {len(df):,} rows, {len(good):,} usable, overall {nat:.1f} per 100")
    series, dropped = screen(series, sums)
    report.append(f"Quality screen: dropped {dropped['state_years']} state-years with unusual reporting and {dropped['spikes']} one-year spikes")
    report.append("State-years dropped: " + ", ".join(sorted(dropped["which"]))[:1500])
    (OUT / "district_iep.json").write_text(json.dumps(series, separators=(",", ":")))
    print("\n".join(report))
    print("districts with any year:", len(series))
    print("Montclair:", series.get("3410560"))


main()
