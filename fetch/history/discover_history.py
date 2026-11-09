"""History discovery for IDEA Atlas (Phase 3).

Lists every historical file the agencies offer, so we can see how far back each
source goes before downloading anything. Writes fetch/reports/history_discovery.json and .md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from discover import DATA_EXT, UA, head_info, links_from_browser, links_from_page  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "fetch" / "reports"

BROWSER = {
    "lea_child_count": "https://data.ed.gov/dataset/idea-section-618-lea-part-b-child-count",
    "lea_environments": "https://data.ed.gov/dataset/idea-section-618-lea-part-b-educational-environments",
    "lea_exiting": "https://data.ed.gov/dataset/idea-section-618-lea-part-b-exiting",
    "state_child_count": "https://data.ed.gov/dataset/idea-section-618-state-level-data-files-part-b-child-count",
    "state_cc_env": "https://data.ed.gov/dataset/idea-section-618-state-part-b-child-count-and-educational-environments",
    "state_environments": "https://data.ed.gov/dataset/idea-section-618-state-part-b-educational-environments",
    "state_exiting": "https://data.ed.gov/dataset/idea-section-618-state-part-b-exiting",
    "static_tables_b": "https://data.ed.gov/dataset/idea-section-618-data-products-static-tables-part-b",
    "crdc": "https://civilrightsdata.ed.gov/data",
}
PAGES = {
    "ccd_agency": "https://nces.ed.gov/ccd/pubagency.asp",
    "f33_agency": "https://nces.ed.gov/ccd/f33agency.asp",
}
DIRS = {
    "census_finance": ("https://www2.census.gov/programs-surveys/school-finances/tables/", r"elsec|school"),
    "saipe": ("https://www2.census.gov/programs-surveys/saipe/datasets/", r"school|sd"),
}
DIGEST_TABLES = ["204.30", "204.40", "204.60", "204.65", "204.70", "219.90", "203.20", "203.10"]


def walk_dir(url: str, keep: str, depth: int = 3) -> list[dict]:
    found, todo, seen = [], [(url, 0)], set()
    while todo:
        u, d = todo.pop()
        if u in seen:
            continue
        seen.add(u)
        try:
            r = requests.get(u, headers=UA, timeout=60)
            r.raise_for_status()
        except Exception:  # noqa: BLE001
            continue
        for href in re.findall(r'href="([^"?][^"]*)"', r.text):
            full = urljoin(u, href)
            if not full.startswith(url) or full == u:
                continue
            if full.endswith("/") and d < depth:
                todo.append((full, d + 1))
            elif DATA_EXT.search(full) and re.search(keep, full, re.I):
                found.append({"url": full, "text": full.rsplit("/", 1)[-1]})
    return found


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for k, u in BROWSER.items():
        try:
            report[k] = links_from_browser(u)
        except Exception as e:  # noqa: BLE001
            report[k] = [{"error": str(e)[:300]}]
    for k, u in PAGES.items():
        try:
            report[k] = links_from_page(u)
        except Exception as e:  # noqa: BLE001
            report[k] = [{"error": str(e)[:300]}]
    for k, (u, keep) in DIRS.items():
        report[k] = walk_dir(u, keep)
    dig = []
    for v in ("d25", "d24", "d23", "d22", "d21", "d20", "d19", "d18", "d17", "d16", "d15", "d14", "d13", "d12", "d11", "d10"):
        for t in DIGEST_TABLES:
            u = f"https://nces.ed.gov/programs/digest/{v}/tables/xls/tabn{t}.xls" + ("x" if v >= "d18" else "")
            h = head_info(u)
            if h.get("status") != 200:
                u2 = u[:-1] if u.endswith("x") else u + "x"
                h2 = head_info(u2)
                if h2.get("status") == 200:
                    u, h = u2, h2
            dig.append({"url": u, "status": h.get("status"), "bytes": h.get("bytes")})
    report["digest"] = dig
    (OUT / "history_discovery.json").write_text(json.dumps(report, indent=1))
    lines = ["# History discovery", ""]
    for k, items in report.items():
        lines.append(f"## {k} ({len(items)})")
        for it in items[:400]:
            lines.append(f"- {it.get('status', '')} {it.get('url', it.get('error', ''))} {it.get('text', '')[:80]}")
        lines.append("")
    (OUT / "history_discovery.md").write_text("\n".join(lines))
    print("\n".join(lines)[:20000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
