"""Discovery step for IDEA Atlas.

Visits each source's landing page (and, where the agency offers one, its
catalog API) and lists every downloadable data file it finds, with size and
date when the server reports them. Writes:

  fetch/reports/discovery.json  - full machine-readable list
  fetch/reports/discovery.md    - short readable summary

Nothing is downloaded in full here; this step only finds the files.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fetch" / "reports"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 IDEA-Atlas-data-check/0.2"}
DATA_EXT = re.compile(r"\.(zip|csv|xlsx?|txt|json|gpkg|7z)(\?|$)", re.I)
TIMEOUT = 60

# Extra places to look, beyond each landing page.
EXTRA = {
    "idea_child_count": [("ckan", "IDEA Section 618 child count LEA")],
    "idea_environments": [("ckan", "IDEA Section 618 educational environments LEA")],
    "idea_exiting": [("ckan", "IDEA Section 618 exiting LEA")],
    "crdc": [("ckan", "Civil Rights Data Collection")],
    "osep_determinations": [("ckan", "IDEA determinations")],
    "saipe": [("dir", "https://www2.census.gov/programs-surveys/saipe/datasets/")],
    # Newer F-33 years are published by the Census Bureau as "school system finances"
    "edge_boundaries": [("page", "https://nces.ed.gov/programs/edge/Geographic/DistrictBoundaries")],
    "edge_zcta": [("page", "https://nces.ed.gov/programs/edge/Geographic/RelationshipFiles")],
    "ccd_directory": [("page", "https://nces.ed.gov/ccd/files.asp"),
                      ("page", "https://nces.ed.gov/ccd/pubagency.asp")],
    "f33": [("page", "https://nces.ed.gov/ccd/f33agency.asp"),
            ("dir", "https://www2.census.gov/programs-surveys/school-finances/tables/")],
}


def get(url: str, **kw):
    return requests.get(url, headers=UA, timeout=TIMEOUT, **kw)


def head_info(url: str) -> dict:
    try:
        r = requests.head(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        return {"status": r.status_code,
                "bytes": int(r.headers.get("Content-Length", 0) or 0),
                "modified": r.headers.get("Last-Modified", "")}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)[:200]}


def links_from_page(url: str) -> list[dict]:
    r = get(url)
    r.raise_for_status()
    found = []
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', r.text, re.I | re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
        full = urljoin(url, href)
        if DATA_EXT.search(full):
            found.append({"url": full, "text": text[:160]})
    return found


def links_from_browser(url: str) -> list[dict]:
    """Render the page in headless Chromium, for sites built with JavaScript.
    Records file links on the page and any data or API addresses it loads."""
    from playwright.sync_api import sync_playwright
    found, api = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.on("response", lambda r: api.append(r.url) if (
            "json" in (r.headers.get("content-type") or "") or DATA_EXT.search(r.url)) else None)
        pg.goto(url, wait_until="networkidle", timeout=90_000)
        pg.wait_for_timeout(4000)
        for a in pg.query_selector_all("a[href]"):
            href = a.get_attribute("href") or ""
            full = urljoin(url, href)
            text = (a.inner_text() or "").strip()
            if DATA_EXT.search(full) or re.search(r"download|data file|lea|district", text, re.I):
                found.append({"url": full, "text": text[:160]})
        b.close()
    for u in dict.fromkeys(api):
        found.append({"url": u, "text": "[loaded by page]"})
    return found


def links_from_ckan(query: str) -> list[dict]:
    api = "https://data.ed.gov/api/3/action/package_search"
    r = get(api, params={"q": query, "rows": 25, "sort": "metadata_modified desc"})
    r.raise_for_status()
    found = []
    for pkg in r.json().get("result", {}).get("results", []):
        for res in pkg.get("resources", []):
            if res.get("url"):
                found.append({"url": res["url"],
                              "text": f'{pkg.get("title", "")} | {res.get("name", "")}'[:200],
                              "dataset": pkg.get("name"),
                              "updated": res.get("last_modified") or pkg.get("metadata_modified")})
    return found


def links_from_dir(url: str, depth: int = 2) -> list[dict]:
    """Walk a plain Apache-style directory listing (used by census.gov)."""
    found, todo = [], [(url, 0)]
    while todo:
        u, d = todo.pop()
        try:
            r = get(u)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            if u == url:
                raise
            continue
        for href in re.findall(r'href="([^"?][^"]*)"', r.text):
            full = urljoin(u, href)
            if not full.startswith(url) or full == u:
                continue
            if full.endswith("/") and d < depth:
                # only follow recent years and school-district folders
                tail = full.rstrip("/").rsplit("/", 1)[-1]
                if re.fullmatch(r"20(2[2-9])", tail) or "school" in tail.lower() or "elsec" in tail.lower():
                    todo.append((full, d + 1))
            elif DATA_EXT.search(full) and ("school" in full.lower() or "elsec" in full.lower()):
                found.append({"url": full, "text": full.rsplit("/", 1)[-1]})
    return found


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "sources.yml").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "sources": []}

    for src in cfg["sources"]:
        entry = {"id": src["id"], "name": src["name"],
                 "expected_year": src["expected_year"], "checked": [], "files": []}
        places = [("page", src["landing"])] + EXTRA.get(src["id"], [])
        seen = set()
        for kind, target in places:
            try:
                fn = {"page": links_from_page, "ckan": links_from_ckan, "dir": links_from_dir,
                      "browser": links_from_browser}[kind]
                items = fn(target)
                entry["checked"].append({"kind": kind, "target": target, "ok": True, "count": len(items)})
            except Exception as e:  # noqa: BLE001
                entry["checked"].append({"kind": kind, "target": target, "ok": False, "error": str(e)[:200]})
                continue
            for it in items:
                if it["url"] in seen:
                    continue
                seen.add(it["url"])
                entry["files"].append(it)
        if not entry["files"] or src["id"] == "ccd_directory":
            try:
                items = links_from_browser(src["landing"])
                entry["checked"].append({"kind": "browser", "target": src["landing"], "ok": True, "count": len(items)})
                for it in items:
                    if it["url"] not in seen:
                        seen.add(it["url"])
                        entry["files"].append(it)
            except Exception as e:  # noqa: BLE001
                entry["checked"].append({"kind": "browser", "target": src["landing"], "ok": False, "error": str(e)[:200]})
        # newest first, so recent years show at the top of the report
        entry["files"].sort(key=lambda f: max([int(y) for y in re.findall(r"(?<!\d)(20[12]\d|1[5-9]2[0-6]|2[0-5]2[1-6])(?!\d)", f["url"])] or [0]), reverse=True)
        # size/date for the first 40 candidates only, to stay polite
        for it in entry["files"][:40]:
            it.update(head_info(it["url"]))
        report["sources"].append(entry)

    (OUT / "discovery.json").write_text(json.dumps(report, indent=2))

    lines = [f"# Discovery report", "", f"Run: {report['run_at']}", ""]
    for s in report["sources"]:
        lines.append(f"## {s['name']}")
        lines.append(f"Expected year: {s['expected_year']}. Files found: {len(s['files'])}.")
        for c in s["checked"]:
            status = f"{c['count']} links" if c["ok"] else f"failed: {c['error']}"
            lines.append(f"- checked {c['kind']} `{c['target']}`: {status}")
        for f in s["files"][:25]:
            size = f"{f.get('bytes', 0) / 1e6:.1f} MB" if f.get("bytes") else "size unknown"
            lines.append(f"  - {f['text'] or 'file'}: {f['url']} ({size})")
        lines.append("")
    (OUT / "discovery.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
