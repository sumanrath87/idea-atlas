"""District share images: collected while the pages are written, then drawn in parallel.

Each image is cached under a name made from its inputs and the drawing code, so a rebuild only
draws images whose figures changed. The publish workflow keeps the cache between runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

JOBS: list = []   # (path relative to the site root, inputs for og_district.make)


def _draw(args):
    cache_file, job = args
    import og_district
    tmp = Path(str(cache_file) + ".tmp")
    og_district.make(tmp, **job)
    os.replace(tmp, cache_file)
    return 1


def make_all(out: Path, cache: Path) -> tuple[int, int]:
    """Write every collected image into out; returns (images, newly drawn)."""
    code = (Path(__file__).with_name("og_district.py").read_bytes() + Path(__file__).with_name("extra_pages.py").read_bytes())
    salt = hashlib.sha1(code).hexdigest()[:10]
    cache.mkdir(parents=True, exist_ok=True)
    plan, todo = [], []
    for rel, job in JOBS:
        h = hashlib.sha1((salt + json.dumps(job, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:20]
        cf = cache / f"{h}.png"
        plan.append((rel, cf))
        if not cf.exists():
            todo.append((cf, job))
    if todo:
        from multiprocessing import Pool
        with Pool(max(1, (os.cpu_count() or 2))) as pool:
            for _ in pool.imap_unordered(_draw, todo, chunksize=64):
                pass
    for rel, cf in plan:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(cf, dst)
        except OSError:
            shutil.copyfile(cf, dst)
    # drop cached images no build uses any more, so the cache does not grow without end
    keep = {cf.name for _, cf in plan}
    for f in cache.glob("*.png"):
        if f.name not in keep:
            f.unlink()
    return len(plan), len(todo)
