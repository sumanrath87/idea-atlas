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
UA = {"User-Agent": "IDEA-Atlas-data-check/0.1 (+https://sumanrath.org/tools/idea-atlas/)"}
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
    "edge_boundaries": [("page", "https://nces.ed.gov/programs/edge/Geographic/DistrictBoundaries")],
    "edge_zcta": [("page", "https://nces.ed.gov/programs/edge/Geographic/RelationshipFiles")],
    "ccd_directory": [("page", "https://nces.ed.gov/ccd/files.asp"),
                      ("page", "https://nces.ed.gov/ccd/pubagency.asp")],
    "f33": [("page", "https://nces.ed.gov/ccd/f33agency.asp")],
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
        except Exception:  # noqa: BLE001
            continue
        for href in re.findall(r'href="([^"?][^"]*)"', r.text):
            full = urljoin(u, href)
            if not full.startswith(url) or full == u:
                continue
            if full.endswith("/") and d < depth:
                # only follow recent years and school-district folders
                tail = full.rstrip("/").rsplit("/", 1)[-1]
                if re.fullmatch(r"20(2[3-9])", tail) or "school" in tail.lower():
                    todo.append((full, d + 1))
            elif DATA_EXT.search(full) and "school" in full.lower():
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
                fn = {"page": links_from_page, "ckan": links_from_ckan, "dir": links_from_dir}[kind]
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
        for f in s["files"][:15]:
            size = f"{f.get('bytes', 0) / 1e6:.1f} MB" if f.get("bytes") else "size unknown"
            lines.append(f"  - {f['text'] or 'file'}: {f['url']} ({size})")
        lines.append("")
    (OUT / "discovery.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
