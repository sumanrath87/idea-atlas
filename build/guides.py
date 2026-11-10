"""Guides for IDEA Atlas: plain-language articles written as Markdown in build/guides/en and build/guides/es.

Each file starts with a short header:
    ---
    title: Least restrictive environment, explained with real numbers
    description: One or two sentences for search results.
    lede: The first paragraph under the title.
    group: start | numbers | indicators | families | essay | reference
    order: 10
    pair: es/ambiente-menos-restrictivo        (the same guide in the other language, if any)
    reviewed: 2026-11-10
    ---
The file's path is its address: build/guides/en/indicators/5-educational-environments.md -> /guides/indicators/5-educational-environments/.
Every "## " heading starts a section. A section called "Beyond compliance" ("Más allá del cumplimiento") and
"Sources" ("Fuentes") get their own styling. "{base}" in links becomes the atlas base path.

Guides are written into the site only when build/guides/PUBLISHED exists (after the author approves them).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

import markdown

E = html.escape
HERE = Path(__file__).resolve().parent / "guides"
ORCID = "https://orcid.org/0000-0002-7497-6335"
AUTHOR = {"en": ("Suman Rath, Ph.D.", "Suman Rath, Ph.D., is an assistant professor of educational leadership at Montclair State University. "
                 "He studies inclusive education, education policy, communities of practice, student voice, and change that starts in schools "
                 "and communities. He built IDEA Atlas."),
          "es": ("Suman Rath, Ph.D.", "Suman Rath, Ph.D., es profesor asistente de liderazgo educativo en Montclair State University. "
                 "Estudia la educación inclusiva, las políticas educativas, las comunidades de práctica, la voz de los estudiantes y el cambio "
                 "que nace en las escuelas y las comunidades. Creó IDEA Atlas.")}
GROUPS = {"en": [("start", "Start here"), ("numbers", "Reading the numbers"), ("indicators", "The federal indicators"), ("essay", "Beyond compliance")],
          "es": [("start", "Para empezar"), ("numbers", "Cómo leer las cifras")]}
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def published() -> bool:
    return (HERE / "PUBLISHED").exists()


def _slugify(t: str) -> str:
    import unicodedata
    a = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", a.lower()).strip("-")[:60]


def load(lang: str) -> list[dict]:
    out = []
    root = HERE / lang
    if not root.exists():
        return out
    for f in sorted(root.rglob("*.md")):
        txt = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
        if not m:
            continue
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] == '"':
                    v = v[1:-1]
                meta[k.strip()] = v
        rel = f.relative_to(root).with_suffix("").as_posix()
        meta["rel"] = "" if rel == "index" else rel
        meta["body"] = m.group(2)
        meta["lang"] = lang
        meta["order"] = int(meta.get("order", 100))
        out.append(meta)
    return out


def url(g: dict, BASE: str) -> str:
    root = "guides/" if g["lang"] == "en" else "es/guias/"
    return BASE + root + (g["rel"] + "/" if g["rel"] else "")


def _sections(body_html: str, lang: str) -> tuple[str, int]:
    """Wrap each h2 and what follows it in a <section>, so the 'On this page' list and screen readers see the structure."""
    parts = re.split(r"(<h2>.*?</h2>)", body_html)
    out, n = [parts[0]], 0
    for i in range(1, len(parts), 2):
        h = re.sub(r"<[^>]+>", "", parts[i][4:-5])
        sid = _slugify(h) or f"s{i}"
        low = h.lower()
        cls = ""
        if low.startswith("beyond compliance") or low.startswith("más allá del cumplimiento"):
            cls = ' class="beyond"'
        elif low in ("sources", "fuentes", "sources and further reading", "fuentes y lecturas"):
            cls = ' class="g-sources"'
        out.append(f'<section aria-labelledby="{sid}"{cls}><h2 id="{sid}">{parts[i][4:-5]}</h2>{parts[i + 1]}</section>')
        n += 1
    return "".join(out), n


def _date(s: str, lang: str) -> str:
    try:
        d = dt.date.fromisoformat(s)
    except Exception:
        return s
    return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}" if lang == "es" else d.strftime("%B %-d, %Y")


def render(g: dict, allg: dict, *, BASE: str, ATLAS_ORIGIN: str, SITE: str, page, extra_list: str = "") -> str:
    lang = g["lang"]
    body_md = g["body"].replace("{base}", BASE)
    md = markdown.Markdown(extensions=["tables", "attr_list", "footnotes", "sane_lists"])
    h = md.convert(body_md)
    h = re.sub(r"<table>", '<div class="table-wrap" role="region" tabindex="0"><table class="profile">', h).replace("</table>", "</table></div>")
    h, _n = _sections(h, lang)
    words = len(re.sub(r"<[^>]+>", " ", h).split())
    minutes = max(2, round(words / 220))
    name, bio = AUTHOR[lang]
    rev = _date(g.get("reviewed", ""), lang)
    if lang == "en":
        byline = f'By <a href="{SITE}/">{E(name)}</a> · Last reviewed {E(rev)} · About {minutes} minutes to read'
        about = f'<aside class="author" aria-labelledby="ab-h"><h2 id="ab-h">About the author</h2><p>{E(bio)}</p><p><a href="{SITE}/">sumanrath.org</a> · <a href="{ORCID}">ORCID</a></p></aside>'
        crumbs = [("IDEA Atlas", BASE), ("Guides", BASE + "guides/")]
        if g["rel"].startswith("indicators/"):
            crumbs.append(("The federal indicators", BASE + "guides/indicators/"))
        note = '<p class="hint">General information, not legal advice. Rules can differ by state; your state education agency and Parent Training and Information Center can tell you how they apply where you live.</p>'
    else:
        byline = f'Por <a href="{SITE}/">{E(name)}</a> · Revisado el {E(rev)} · Unos {minutes} minutos de lectura'
        about = f'<aside class="author" aria-labelledby="ab-h"><h2 id="ab-h">Sobre el autor</h2><p>{E(bio)}</p><p><a href="{SITE}/">sumanrath.org</a> · <a href="{ORCID}">ORCID</a></p></aside>'
        crumbs = [("IDEA Atlas", BASE + "es/"), ("Guías", BASE + "es/guias/")]
        note = '<p class="hint">Información general, no asesoría legal. Las reglas pueden variar según el estado; la agencia de educación de su estado y su Centro de Información y Capacitación para Padres pueden explicarle cómo se aplican donde usted vive.</p>'
    related = [allg[r.strip()] for r in g.get("related", "").split(",") if r.strip() in allg]
    rel_html = ""
    if related:
        hd = "Keep reading" if lang == "en" else "Siga leyendo"
        rel_html = (f'<nav class="related" aria-labelledby="rel-h"><h2 id="rel-h">{hd}</h2><ul>' +
                    "".join(f'<li><a href="{url(r, BASE)}">{E(r["title"])}</a><span class="sub">{E(r.get("description", ""))}</span></li>' for r in related) +
                    "</ul></nav>")
    path = url(g, BASE)
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "description": g.get("description", ""),
          "inLanguage": lang, "dateModified": g.get("reviewed", ""), "mainEntityOfPage": ATLAS_ORIGIN + path,
          "author": {"@type": "Person", "name": "Suman Rath", "honorificSuffix": "Ph.D.", "url": SITE + "/", "sameAs": [ORCID],
                     "affiliation": {"@type": "Organization", "name": "Montclair State University"}},
          "publisher": {"@type": "Organization", "name": "IDEA Atlas", "url": ATLAS_ORIGIN + BASE},
          "image": ATLAS_ORIGIN + BASE + "assets/og.png"}
    extra_head = ('<meta property="og:title" content="' + E(g["title"]) + '"><meta property="og:description" content="' + E(g.get("description", "")) + '">'
                  '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    body = f"""
<article class="guide">
<h1>{E(g["title"])}</h1>
<p class="lede">{E(g.get("lede", ""))}</p>
<p class="byline">{byline}</p>
{h}
{extra_list}
{note}
{about}
{rel_html}
</article>"""
    pair = g.get("pair")
    alt = BASE + pair + "/" if pair else None
    return page(g["title"], body, desc=g.get("description", "")[:300], path=path, scripts=("atlas.js",), crumbs=crumbs,
                lang=lang, alt=alt, extra_head=extra_head)


def build(*, BASE: str, ATLAS_ORIGIN: str, SITE: str, page, write) -> list[str]:
    """Write every guide and both hubs. Returns paths for the sitemap."""
    paths = []
    for lang in ("en", "es"):
        gs = load(lang)
        allg = {g["rel"]: g for g in gs}
        root = "guides/" if lang == "en" else "es/guias/"
        for g in gs:
            if g["rel"] == "":
                continue
            extra = ""
            if g["rel"] == "indicators":
                kids = sorted([k for k in gs if k["rel"].startswith("indicators/")], key=lambda k: k["order"])
                extra = _list_html(kids, BASE, "All 18 indicators", "ind-all")
            write(root + g["rel"] + "/index.html", render(g, allg, BASE=BASE, ATLAS_ORIGIN=ATLAS_ORIGIN, SITE=SITE, page=page, extra_list=extra))
            paths.append(root + g["rel"] + "/")
        write(root + "index.html", hub(gs, lang, BASE=BASE, page=page))
        paths.append(root)
    return paths


def _list_html(items, BASE, heading, hid):
    lis = "".join(f'<li><a href="{url(k, BASE)}">{E(k["title"])}</a><span class="sub">{E(k.get("description", ""))}</span></li>' for k in items)
    return f'<section aria-labelledby="{hid}"><h2 id="{hid}">{E(heading)}</h2><ul class="guide-cards">{lis}</ul></section>'


def hub(gs: list[dict], lang: str, *, BASE: str, page) -> str:
    intro = next((g for g in gs if g["rel"] == ""), None)
    secs = []
    for key, label in GROUPS[lang]:
        items = sorted([g for g in gs if g.get("group") == key and g["rel"] and not g["rel"].startswith("indicators/")], key=lambda g: g["order"])
        if items:
            secs.append(_list_html(items, BASE, label, "grp-" + key))
    if lang == "en":
        title = "Guides"
        lede = intro.get("lede") if intro else "Plain-language guides to special education data: what the numbers mean, what the law requires, and what to ask."
        crumbs = [("IDEA Atlas", BASE)]
        alt = BASE + "es/guias/"
        desc = "Plain-language guides to special education data and the law: reading district figures, least restrictive environment, discipline, disputes, and the federal indicators."
    else:
        title = "Guías"
        lede = intro.get("lede") if intro else "Guías en palabras sencillas sobre los datos de educación especial: qué significan las cifras, qué exige la ley y qué preguntar."
        crumbs = [("IDEA Atlas", BASE + "es/")]
        alt = BASE + "guides/"
        desc = "Guías en palabras sencillas sobre los datos de educación especial y la ley."
    body = f'<h1>{E(title)}</h1><p class="lede">{E(lede)}</p>' + "".join(secs)
    return page(title, body, desc=desc, path=BASE + ("guides/" if lang == "en" else "es/guias/"), scripts=("atlas.js",), crumbs=crumbs, lang=lang, alt=alt)
