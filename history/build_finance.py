"""District spending per student over time, in 2024 dollars.
F-33 school district finance files (NCES, FY1990, FY1992, FY1995-FY2018; dollars) and the Census Bureau's
elsec spreadsheets (FY2019-FY2023; thousands of dollars). Current spending (TCURELSC) / fall membership (V33).
Inflation: CPI-U, U.S. city average, all items (BLS, via FRED series CUUS0000SA0); a fiscal year (July-June)
uses the mean of the second half of the prior year and the first half of the year.
Writes history/output/district_spend.json: {leaid: {fiscal_year: dollars_2024}}"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/hist/raw/finance")
OUT = Path(__file__).resolve().parent / "output"
# CPI-U semiannual averages (H1, H2), FRED CUUS0000SA0
CPI = {1989: (None, 122.6), 1990: (128.7, 132.6), 1991: (135.2, 137.2), 1992: (139.2, 141.4), 1993: (143.7, 145.3), 1994: (147.2, 149.3),
       1995: (151.5, 153.2), 1996: (155.8, 157.9), 1997: (159.9, 161.2), 1998: (162.3, 163.7), 1999: (165.4, 167.8),
       2000: (170.8, 173.6), 2001: (176.6, 177.5), 2002: (178.9, 180.9), 2003: (183.3, 184.6), 2004: (187.6, 190.2),
       2005: (193.2, 197.4), 2006: (200.6, 202.6), 2007: (205.709, 208.976), 2008: (214.429, 216.177), 2009: (213.139, 215.935),
       2010: (217.535, 218.576), 2011: (223.598, 226.280), 2012: (228.850, 230.338), 2013: (232.366, 233.548), 2014: (236.384, 237.088),
       2015: (236.265, 237.769), 2016: (238.778, 241.237), 2017: (244.076, 246.163), 2018: (250.089, 252.125), 2019: (254.412, 256.903),
       2020: (257.557, 260.065), 2021: (266.236, 275.703), 2022: (288.347, 296.963), 2023: (302.408, 306.996), 2024: (312.145, 315.233)}


def fy_cpi(fy: int) -> float:
    return (CPI[fy - 1][1] + CPI[fy][0]) / 2


def read(z: Path) -> pd.DataFrame:
    with zipfile.ZipFile(z) as zf:
        n = [x for x in zf.namelist() if x.lower().endswith(".txt")][0]
        b = zf.read(n)
    first = b[:200].decode("latin-1")
    if first.startswith("LEAID"):
        return pd.read_csv(io.BytesIO(b), sep="\t", dtype=str, encoding="latin-1", low_memory=False)
    df = pd.read_csv(io.BytesIO(b), sep="\t", dtype=str, header=None, encoding="latin-1", low_memory=False)
    return df.rename(columns={0: "LEAID", 13: "V33", 96: "TCURELSC"})   # FY1992 layout: fields 1, 14, 97


FILES = {1990: "sdf901a.txt.zip", 1992: "sdf921a.txt.zip", 1995: "sdf95c1d.txt.zip", 1996: "sdf96c1b.txt.zip", 1997: "sdf97d1a.txt.zip",
         1998: "sdf981e.txt.zip", 1999: "sdf991c.txt.zip", 2000: "sdf001d.txt.zip", 2001: "sdf011d.txt.zip", 2002: "sdf021ctxt.zip",
         2003: "sdf031b.txt.zip", 2004: "sdf041b.txt.zip", 2005: "sdf051c.txt.zip", 2006: "sdf061a.txt.zip", 2007: "sdf071a.txt.zip",
         2008: "sdf081a_txt.zip", 2009: "SDF091a_txt.zip", 2010: "SDF101a_txt.zip", 2011: "sdf11_1a_txt.zip", 2012: "sdf121a.zip",
         2013: "sdf13_1a.zip", 2014: "sdf14_1a_flat.zip", 2015: "sdf15_1a.zip", 2016: "Sdf16_1a.zip", 2017: "Sdf17_1a.zip", 2018: "Sdf18_1a.zip"}


def main():
    OUT.mkdir(exist_ok=True)
    series, rep = {}, []
    frames = []
    for fy, f in FILES.items():
        try:
            d = read(RAW / f)[["LEAID", "V33", "TCURELSC"]]
            d["mult"] = 1
            frames.append((fy, d))
        except Exception as e:  # noqa: BLE001
            rep.append(f"FY{fy}: {e}")
    for fy in range(2019, 2024):
        f = RAW / f"elsec{str(fy)[2:]}.xlsx"
        f = f if f.exists() else RAW / f"elsec{str(fy)[2:]}.xls"
        d = pd.read_excel(f, sheet_name=0, dtype=str)
        d = d.rename(columns={"NCESID": "LEAID"})[["LEAID", "V33", "TCURELSC"]]
        d["mult"] = 1000
        frames.append((fy, d))
    base = fy_cpi(2024)
    for fy, d in frames:
        v = pd.to_numeric(d.V33, errors="coerce")
        c = pd.to_numeric(d.TCURELSC, errors="coerce") * d["mult"]
        ok = (v >= 50) & (c > 0)
        pp = (c / v)[ok] * base / fy_cpi(fy)
        lid = d.LEAID[ok].astype(str).str.strip().str.zfill(7)
        sane = (pp > 2000) & (pp < 100000)
        for l, x in zip(lid[sane], pp[sane]):
            series.setdefault(l, {})[fy] = int(round(x, -1))
        rep.append(f"FY{fy}: {int(ok.sum()):,} districts, median ${pp[sane].median():,.0f} (2024 dollars)")
    # one-year spikes (a year more than 40% away from both neighbours, which agree with each other)
    spikes = 0
    for l, ys in series.items():
        yrs = sorted(ys)
        for i in range(1, len(yrs) - 1):
            a, b, c = ys[yrs[i - 1]], ys[yrs[i]], ys[yrs[i + 1]]
            if None in (a, b, c):
                continue
            if abs(a - c) / max(a, c) < 0.2 and abs(b - (a + c) / 2) / ((a + c) / 2) > 0.4:
                ys[yrs[i]] = None
                spikes += 1
        series[l] = {y: v for y, v in ys.items() if v is not None}
    rep.append(f"one-year spikes removed: {spikes}")
    (OUT / "district_spend.json").write_text(json.dumps(series, separators=(",", ":")))
    print("\n".join(rep))
    print("Montclair:", series.get("3410560"))


main()
