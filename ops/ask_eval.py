"""Grade every question in ops/ask_corpus.json.gz against a local build and report what the box gets wrong.

    ATLAS_FAST=1 python build/site.py && (cd site && python -m http.server 8765 &)
    python ops/ask_corpus.py && python ops/ask_eval.py [--lang en|es] [--only kind] [--limit N] [--show 40]

Needs: pip install playwright && playwright install chromium.
"""
import argparse, gzip, json, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8765/tools/idea-atlas/")
ap.add_argument("--lang"); ap.add_argument("--only"); ap.add_argument("--limit", type=int); ap.add_argument("--show", type=int, default=25)
ap.add_argument("--out", default="/tmp/ask_eval.json")
A = ap.parse_args()
Q = json.load(gzip.open(ROOT / "ops" / "ask_corpus.json.gz", "rt"))

RUN = """async (qs) => { const out = [];
  for (const q of qs) { try { const r = await window.__ideaQA(q);
      const d = document.createElement('div'); d.innerHTML = r.html;
      r.cards = Array.from(d.querySelectorAll('h4')).map(h => h.textContent.trim()).slice(0, 6);
      r.notes = Array.from(d.querySelectorAll('.qa-note')).map(h => h.textContent.trim().slice(0, 80));
      r.text = d.textContent.replace(/\\s+/g, ' ').trim().slice(0, 220); delete r.html; out.push(r);
    } catch (e) { out.push({kind: 'ERROR', err: String(e).slice(0, 200)}); } }
  return out; }"""

BAD_FOR_OFFTOPIC = {"district", "compare", "state", "states", "nation"}


def grade(it, r):
    x, k = it["x"], r.get("kind")
    if k == "ERROR":
        return False, "script error"
    if x == "district":
        if k == "district" and r["ids"] and r["ids"][0] in it["ok"]:
            return True, ""
        if k == "choose":
            return bool(it.get("amb_ok")), "asked to choose"
        if k == "district":
            return False, "wrong district"
        if k == "compare" and r["ids"] and r["ids"][0] in it["ok"]:
            return False, "extra district found"
        return False, "no district (" + k + ")"
    if x == "compare":
        if k != "compare":
            return False, "not a comparison (" + k + ")"
        miss = [ok for ok in it["oks"] if not set(ok) & set(r["ids"])]
        return (not miss), ("missed %d of %d" % (len(miss), len(it["oks"])) if miss else "")
    if x == "state":
        return (k == "state" and r["st"] == it["st"]), ("kind " + k + " st " + str(r.get("st")))
    if x == "states":
        return (k == "states" and set(it["sts"]) <= set(r["sts"])), ("kind " + k)
    if x == "nation":
        return k == "nation", "kind " + k
    if x == "definition":
        return bool(r.get("defn")) or bool(r.get("def")), "no definition (" + k + ")"
    if x == "info":
        good = k in ("info", "definition", "guides") and r["kind"] not in BAD_FOR_OFFTOPIC or (it["intent"] == "rank" and r.get("rank"))
        return good, "kind " + k
    if x == "unsupported":
        return bool(r.get("unsup")), "no 'not covered' note (" + k + ")"
    if x == "offtopic":
        return k not in BAD_FOR_OFFTOPIC and k not in ("guides",), "kind " + k
    if x == "situation":
        g = r.get("guides", [])[:3]
        if r.get("defn") and set(it["rels"]) & {"glossary", "glosario"}:
            return True, ""
        data_rel = {"indicators/1-graduation", "indicators/2-dropout", "indicators/4-suspension-and-expulsion", "indicators/5-educational-environments",
                    "indicadores/1-graduacion", "indicadores/2-abandono-escolar", "indicadores/4-suspension-y-expulsion", "indicadores/5-ambientes-educativos"}
        if k in ("nation", "state", "district") and set(it["rels"]) & data_rel:
            return True, ""
        hit = set(g) & set(it["rels"])
        return bool(hit), ("guides " + ",".join(g[:3]) if g else "no guides (" + k + ")")
    return False, "unknown"


def main():
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch(); 
        for lang in ("en", "es"):
            if A.lang and A.lang != lang:
                continue
            items = [it for it in Q[lang] if not A.only or it["x"] == A.only][: A.limit]
            pg = b.new_page(); pg.goto(A.url + ("es/" if lang == "es" else "") + "?qatest=1"); pg.wait_for_function("!!window.__ideaQA")
            t0 = time.time(); rs = []
            for s in range(0, len(items), 250):
                rs += pg.evaluate(RUN, [it["q"] for it in items[s:s + 250]])
            res[lang] = (items, rs); pg.close()
            print(f"{lang}: {len(items)} questions in {time.time() - t0:.0f}s", file=sys.stderr)
        b.close()
    report = {}
    for lang, (items, rs) in res.items():
        by = defaultdict(lambda: [0, 0]); fails = defaultdict(list); why = defaultdict(Counter)
        for it, r in zip(items, rs):
            ok, w = grade(it, r)
            by[it["x"]][0 if ok else 1] += 1
            if not ok:
                fails[it["x"]].append({"q": it["q"], "why": w, "got": r.get("kind"), "ids": r.get("ids", [])[:3], "cards": r.get("cards"), "text": r.get("text", "")[:160]})
                why[it["x"]][w.split(" (")[0]] += 1
        tot_ok = sum(v[0] for v in by.values()); tot = sum(v[0] + v[1] for v in by.values())
        print(f"\n== {lang}: {tot_ok}/{tot} correct ({100 * tot_ok / max(tot, 1):.1f}%)")
        for x, (ok, bad) in sorted(by.items()):
            print(f"  {x:12s} {ok:6d} ok {bad:5d} wrong  {100 * ok / (ok + bad):5.1f}%   " + ", ".join(f"{w}: {c}" for w, c in why[x].most_common(4)))
        report[lang] = fails
        for x, fl in fails.items():
            for f in fl[: A.show if (A.only or A.lang) else 4]:
                print(f"    [{x}] {f['q']!r} -> {f['why']} | {f['text'][:120]}")
    json.dump(report, open(A.out, "w"), ensure_ascii=False, indent=0)


main()
