"""Download the historical files chosen from history_discovery.json into fetch/history/raw/.
Writes fetch/reports/history_manifest.md with sizes and checksums."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "fetch" / "history" / "raw"
REP = ROOT / "fetch" / "reports"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36 IDEA-Atlas-history/0.1"}


def pick() -> list[str]:
    d = json.loads((REP / "history_discovery.json").read_text())
    urls = []
    urls += [x["url"] for x in d["digest"] if x.get("status") == 200]
    for x in d["ccd_agency"]:
        u = x.get("url", "")
        if re.search(r"/(pau\d\ddat\w*|ccdagn97|ag\d{3}[a-c](_supp)?(_txt|_dat)?)\.zip$", u, re.I) or re.search(r"pau\w*lay\w*\.txt$", u, re.I):
            urls.append(u)
        elif re.search(r"ccd_lea_(052|2_89|002089|029)_\d{4}.*?(csv|txt)?\.zip$", u, re.I) and "sas" not in u.lower():
            urls.append(u)
        elif re.search(r"_(LEA_)?(Membership|IDEA|Directory)_Layout\.xlsx?$|Master_Layout", u):
            urls.append(u)
    for x in d["f33_agency"]:
        u = x.get("url", "")
        if re.search(r"sdf\w*(\.txt|_txt|txt|_flat|data)\.zip$|sdf1\d_1a\.zip$|sdf121a\.zip$|sdf13_1a\.zip$|lay\w*\.txt$|layout\.txt$", u, re.I) and "sas" not in u.lower():
            urls.append(u)
    for x in d["census_finance"]:
        u = x.get("url", "")
        if re.search(r"/elsec\d\d\.(txt|xlsx?)$", u) and int(re.search(r"elsec(\d\d)", u).group(1)) in range(19, 24):
            urls.append(u)
    for x in d["crdc"]:
        u = x.get("url", "")
        if re.search(r"/(2009-10|2011-12|2013-14|2015-16|2017-18|2020-21|2021-22)-crdc-data\.zip$", u):
            urls.append(u)
    # SAIPE school district estimates, 1995 onward
    base = "https://www2.census.gov/programs-surveys/saipe/datasets/"
    for y in range(1995, 2024):
        for sub in (f"{y}/{y}-school-districts/",):
            try:
                r = requests.get(base + sub, headers=UA, timeout=60)
                if r.status_code != 200:
                    continue
                for href in re.findall(r'href="([^"?][^"]*)"', r.text):
                    if re.search(r"\.(txt|xls|xlsx)$", href, re.I):
                        urls.append(urljoin(base + sub, href))
            except Exception:  # noqa: BLE001
                pass
    return list(dict.fromkeys(urls))


def name_for(u: str) -> str:
    tail = u.rsplit("/", 1)[-1].replace(" ", "_")
    m = re.search(r"/digest/(d\d\d)/", u)
    if m:
        return f"digest_{m.group(1)}_{tail}"
    m = re.search(r"/saipe/datasets/(\d{4})/", u)
    if m and not tail.startswith(m.group(1)):
        return f"saipe_{m.group(1)}_{tail}"
    return tail


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    urls = pick()
    lines = ["# History downloads", "", "| File | Bytes | SHA-256 | Source |", "|---|---|---|---|"]
    ok = 0
    for u in urls:
        dest = RAW / name_for(u)
        try:
            with requests.get(u, headers=UA, stream=True, timeout=300) as r:
                r.raise_for_status()
                h = hashlib.sha256()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        h.update(chunk)
            lines.append(f"| {dest.name} | {dest.stat().st_size:,} | {h.hexdigest()[:16]} | {u} |")
            ok += 1
        except Exception as e:  # noqa: BLE001
            lines.append(f"| FAILED | | | {u} ({str(e)[:80]}) |")
    (REP / "history_manifest.md").write_text("\n".join(lines))
    print(f"{ok} of {len(urls)} files downloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
