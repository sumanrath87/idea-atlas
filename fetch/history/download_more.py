"""Second history download: district IEP counts and enrollment for 2018-19 onward.
CCD files (NCES) and the Department of Education's own district child count files (found through data.ed.gov's catalog API)."""
import json
import re
import sys
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent / "raw"
REP = Path(__file__).resolve().parent.parent / "reports"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36 IDEA-Atlas-history/0.2"}
CCD = ["https://nces.ed.gov/ccd/data/zip/ccd_lea_2_89_1819_l_1a_091019.zip", "https://nces.ed.gov/ccd/Data/zip/ccd_lea_2_89_1920_l_1a_082120.zip",
       "https://nces.ed.gov/ccd/data/zip/ccd_lea_052_1819_l_1a_091019.zip", "https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_1920_l_1a_082120.zip",
       "https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2021_l_1a_080621.zip", "https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2122_l_1a_071722.zip",
       "https://nces.ed.gov/ccd/data/zip/ccd_lea_052_2223_l_1a_083023.zip", "https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2324_l_1a_073124.zip"]


def get(u, dest):
    with requests.get(u, headers=UA, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for c in r.iter_content(1 << 20):
                f.write(c)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = []
    urls = list(CCD)
    for ds in ("idea-section-618-lea-part-b-child-count", "16968dd3-87bd-4e4a-92ed-50f03e6c4941"):
        try:
            r = requests.get("https://data.ed.gov/api/3/action/package_show", params={"id": ds}, headers=UA, timeout=60)
            res = r.json()["result"]["resources"]
            for x in res:
                u = x.get("url", "")
                log.append(f"catalog: {x.get('name')} {u}")
                if re.search(r"lea(20(1[89]|2[0-3]))-\d\d\.csv$", u, re.I):
                    urls.append(u)
            break
        except Exception as e:  # noqa: BLE001
            log.append(f"catalog {ds} failed: {str(e)[:120]}")
    for u in dict.fromkeys(urls):
        try:
            get(u, RAW / u.rsplit("/", 1)[-1])
            log.append(f"ok {u}")
        except Exception as e:  # noqa: BLE001
            log.append(f"FAILED {u} {str(e)[:100]}")
    (REP / "history_more.md").write_text("\n".join(log))
    print("\n".join(log))


sys.exit(main())
