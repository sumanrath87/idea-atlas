"""State measures: IDEA Part B SPP/APR indicator files (OSEP, sites.ed.gov/idea) and the state dispute resolution file (data.ed.gov).
Tries the newest year first; reads each indicator page for its .xlsx link and falls back to the usual file name."""
import re
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent / "raw"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36 IDEA-Atlas/0.3"}
DISPUTE = "https://data.ed.gov/dataset/19666ae7-6e53-4cb7-8b86-31795955de11/resource/3af450f2-c3fa-421a-87ae-7d172349e1d9/download/bdispres2023-24.xlsx"


def get(u, dest):
    r = requests.get(u, headers=UA, timeout=120)
    r.raise_for_status()
    if len(r.content) < 2000 or r.content[:2] != b"PK":
        raise ValueError("not an xlsx")
    dest.write_bytes(r.content)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = []
    for ind in (8, 11, 12, 1):
        done = False
        for ffy in ("2024", "2023", "2022"):
            page = f"https://sites.ed.gov/idea/idea-files/part-b-spp-apr-indicator-b{ind}-ffy{ffy}/"
            links = []
            try:
                h = requests.get(page, headers=UA, timeout=60)
                if h.ok:
                    links = re.findall(r'href="([^"]+\.xlsx)"', h.text)
            except Exception as e:
                log.append(f"page {page}: {e}")
            links.append(f"https://sites.ed.gov/idea/files/SPPAPR_B{ind:02d}_FFY{ffy}.xlsx")
            for q in (f"SPPAPR_B{ind:02d}_FFY{ffy}", f"SPPAPR_B{ind:02d}", f"B{ind:02d}_FFY{ffy}"):
                try:                                     # the site's own media search finds files with unusual names
                    j = requests.get("https://sites.ed.gov/idea/wp-json/wp/v2/media", params={"search": q, "per_page": 50}, headers=UA, timeout=60).json()
                    for it in j if isinstance(j, list) else []:
                        u = it.get("source_url", "")
                        log.append(f"media {q}: {u}")
                        if u.endswith(".xlsx") and f"FFY{ffy}" in u.upper().replace("FFY_", "FFY") and u not in links:
                            links.append(u)
                except Exception as e:
                    log.append(f"media {q}: {e}")
            for u in links:
                try:
                    get(u, RAW / f"spp_B{ind:02d}_FFY{ffy}.xlsx")
                    log.append(f"ok B{ind} FFY{ffy} {u}")
                    done = True
                    break
                except Exception as e:
                    log.append(f"miss B{ind} FFY{ffy} {u}: {e}")
            if done:
                break
    try:
        get(DISPUTE, RAW / "dispute_2023-24.xlsx")
        log.append("ok dispute")
    except Exception as e:
        log.append(f"miss dispute: {e}")
    print("\n".join(log))


if __name__ == "__main__":
    main()
