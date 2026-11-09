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
    # data.ed.gov dataset pages are built with JavaScript, so they are opened in a browser.
    # The direct links are the latest files known when this was written; they are re-checked each run.
    "idea_child_count": [("browser", "https://data.ed.gov/dataset/idea-section-618-lea-part-b-child-count"),
                         ("direct", "https://data.ed.gov/dataset/16968dd3-87bd-4e4a-92ed-50f03e6c4941/resource/00a5a1b6-835b-4f4e-9de6-bfb43f877087/download/bchildcountdisabilitycategorylea2024-25.csv")],
    "idea_environments": [("browser", "https://data.ed.gov/dataset/idea-section-618-lea-part-b-educational-environments"),
                          ("direct", "https://data.ed.gov/dataset/5f068d7a-c35a-484f-94a8-0c129032e231/resource/50569ac2-24b6-487b-9f45-4a3be65e4e5f/download/beducationalenvironmentslea2024-25.csv")],
    "idea_exiting": [("browser", "https://data.ed.gov/dataset/idea-section-618-lea-part-b-exiting"),
                     ("browser", "https://data.ed.gov/dataset/idea-section-618-data-products")],
    "osep_determinations": [("browser", "https://www.ed.gov/laws-and-policy/individuals-disabilities/idea/idea-files")],
    "saipe": [("dir", "https://www2.census.gov/programs-surveys/saipe/datasets/")],
    # Newer F-33 years are published by the Census Bureau as "school system finances"
    "edge_boundaries": [("page", "https://nces.ed.gov/programs/edge/Geographic/DistrictBoundaries")],
    "edge_zcta": [("page", "https://nces.ed.gov/programs/edge/Geographic/RelationshipFiles")],
    # NCES file service: /api/File/{fiscal}/{level 5 = district}/{year}/{file}/{version}/{year}
    "ccd_directory": [("json", "https://nces.ed.gov/ccd/datatables/api/File/0/5/0/7/0/0"),
                      ("page", "https://nces.ed.gov/ccd/pubagency.asp")],
    "f33": [("json", "https://nces.ed.gov/ccd/datatables/api/File/1/5/0/5/0/0"),
            ("page", "https://nces.ed.gov/ccd/f33agency.asp"),
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
        if DATA_EXT.search(u) and not re.search(r"\.js(on)?(\?|$)", u):
            found.append({"url": u, "text": "[loaded by page]"})
    return found


def links_from_json(url: str) -> list[dict]:
    """Read a JSON data service and collect every file address inside it."""
    r = get(url)
    r.raise_for_status()
    data, found = r.json(), []
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "raw" / (re.sub(r"\W+", "_", url)[-60:] + ".json")).write_text(json.dumps(data, indent=1)[:2_000_000])

    def walk(x, ctx):
        if isinstance(x, dict):
            label = " | ".join(str(x[k]) for k in ("schoolYear", "title", "name", "description", "year") if isinstance(x.get(k), (str, int)))[:200]
            for v in x.values():
                walk(v, label or ctx)
        elif isinstance(x, list):
            for v in x:
                walk(v, ctx)
        elif isinstance(x, str) and DATA_EXT.search(x):
            found.append({"url": urljoin("https://nces.ed.gov/ccd/", x), "text": ctx})
    walk(data, "")
    return found


def links_from_direct(url: str) -> list[dict]:
    return [{"url": url, "text": url.rsplit("/", 1)[-1]}]


def links_from_ckan(query: str) -> list[dict]:
    api = "https://catalog.data.gov/api/3/action/package_search"
    r = get(api, params={"q": query, "rows": 20, "fq": "organization:ed-gov"})
    if r.status_code != 200 or not r.text.lstrip().startswith("{"):
        r = get(api, params={"q": query, "rows": 20})
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


def links_from_dir(url: str, depth: int = 3) -> list[dict]:
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
                if re.fullmatch(r"20(2[2-9])", tail) or "school" in tail.lower() or "elsec" in tail.lower() or "finance" in tail.lower():
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
                      "browser": links_from_browser, "json": links_from_json,
                      "direct": links_from_direct}[kind]
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
        if not entry["files"]:
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
