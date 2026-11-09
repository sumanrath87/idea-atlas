"""Download step for IDEA Atlas.

Fetches every file in config/confirmed.yml once, into fetch/raw/ (not kept in
git), and writes fetch/reports/manifest.json and manifest.md with each file's
size, server date, download date, and SHA-256 checksum. The workflow then
stores the files as a dated GitHub release.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import json
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "fetch" / "raw"
OUT = ROOT / "fetch" / "reports"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 IDEA-Atlas-data-check/0.2"}


def expand(entry: dict) -> list[str]:
    if "url" in entry:
        return [entry["url"]]
    if "pattern" in entry:
        disc = json.loads((OUT / "discovery.json").read_text())
        urls = {f["url"] for s in disc["sources"] for f in s["files"]}
        return sorted(u for u in urls if fnmatch.fnmatch(u, entry["pattern"]))
    return []


def fetch(url: str, dest: Path) -> dict:
    for attempt in range(3):
        try:
            with requests.get(url, headers=UA, stream=True, timeout=120) as r:
                r.raise_for_status()
                h = hashlib.sha256()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        h.update(chunk)
                return {"ok": True, "bytes": dest.stat().st_size, "sha256": h.hexdigest(),
                        "server_date": r.headers.get("Last-Modified", "")}
        except Exception as e:  # noqa: BLE001
            err = str(e)[:200]
            time.sleep(10 * (attempt + 1))
    return {"ok": False, "error": err}


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "confirmed.yml").read_text())
    RAW.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    rows, failed = [], 0
    for entry in cfg["files"]:
        if "local" in entry:
            p = ROOT / entry["local"]
            rows.append({"source": entry["source"], "year": entry["year"], "file": p.name, "url": entry["local"],
                         "ok": p.exists(), "bytes": p.stat().st_size if p.exists() else 0,
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "",
                         "server_date": "", "downloaded": today})
            continue
        urls = expand(entry)
        if not urls:
            rows.append({"source": entry["source"], "year": entry["year"], "file": "", "url": entry.get("pattern", ""),
                         "ok": False, "error": "no matching files"})
            failed += 1
            continue
        for url in urls:
            name = f'{entry["source"]}__{url.rsplit("/", 1)[-1]}'.replace(" ", "_")
            res = fetch(url, RAW / name)
            failed += 0 if res["ok"] else 1
            rows.append({"source": entry["source"], "year": entry["year"], "file": name, "url": url,
                         "downloaded": today, **res})
            print(("OK  " if res["ok"] else "FAIL"), name, res.get("bytes", res.get("error")))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps({"downloaded": today, "files": rows}, indent=2))
    total = sum(r.get("bytes", 0) for r in rows if r.get("ok"))
    lines = ["# Download manifest", "", f"Downloaded: {today}. Files: {len(rows)}. Failed: {failed}. "
             f"Total size: {total / 1e6:.0f} MB.", "",
             "| Source | Year | File | Size | Server date | Checksum (first 12) |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("ok"):
            lines.append(f'| {r["source"]} | {r["year"]} | {r["file"]} | {r["bytes"] / 1e6:.1f} MB | '
                         f'{r.get("server_date", "")} | {r["sha256"][:12]} |')
        else:
            lines.append(f'| {r["source"]} | {r["year"]} | {r.get("file") or r["url"]} | failed | {r.get("error", "")} | |')
    (OUT / "manifest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
