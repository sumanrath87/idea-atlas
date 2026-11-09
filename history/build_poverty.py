"""Child poverty over time: Census SAIPE school district estimates, 2003 onward (national ussdYY.txt files).
Each line: state FIPS, district code, name, total population, children 5-17, children 5-17 in poverty.
Writes history/output/district_poverty.json: {leaid: {year: per100}}"""
import json
import re
import sys
from pathlib import Path

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/hist/raw/saipe")
OUT = Path(__file__).resolve().parent / "output"
series = {}
for f in sorted(RAW.glob("saipe_*_ussd*.txt")):
    year = int(re.search(r"saipe_(\d{4})_", f.name).group(1))
    n = 0
    for line in f.read_text(encoding="latin-1").splitlines():
        m = re.match(r"^(\d\d) (\d{5}) (.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s+\S+\.txt", line)
        if not m:
            continue
        kids, poor = int(m.group(5)), int(m.group(6))
        if kids >= 50:
            series.setdefault(m.group(1) + m.group(2), {})[year] = round(100 * poor / kids, 1)
            n += 1
    print(year, n)
(OUT / "district_poverty.json").write_text(json.dumps(series, separators=(",", ":")))
print("Montclair:", series.get("3410560"))
