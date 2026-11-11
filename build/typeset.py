"""Typesetting for the text people read: curly quotes and apostrophes, en dashes in year ranges,
and no line breaks inside "Table 3" or "15 %". Tags, attributes, scripts, styles and code are left alone."""
import re

_SPLIT = re.compile(r"(<[^>]*>)")
_SKIP_OPEN = re.compile(r"<(script|style|pre|code|textarea)\b", re.I)
_YEARS = re.compile(r"(?<![\d\-/])((?:19|20)\d\d)-((?:19|20)?\d\d)(?![\d\-/])")
_SPACED = re.compile(r"(?<=\w) - (?=\w)")
_NBSP_WORD = re.compile(r"\b(Table|Figure|Tabla|Figura|Section|Sección|Part|Parte|page|página) (\d)")
_NBSP_PCT = re.compile(r"(\d) %")
_APOS_IN = re.compile(r"(?<=\w)'(?=\w)")
_APOS_DECADE = re.compile(r"'(?=\d\ds\b)")
_OPEN_S = re.compile(r"(?<=[\s(\[\u2014\u2013/])'|^'")
_OPEN_D = re.compile(r"(?<=[\s(\[\u2014\u2013/])\"|^\"")
_BLOCK = re.compile(r"</?(p|li|h[1-6]|td|th|dt|dd|div|section|br|caption|figcaption|summary|title|option|blockquote|label|button)\b", re.I)


def _text(seg: str, prev: str) -> str:
    if "&" in seg:
        seg = seg.replace("&#x27;", "'").replace("&#39;", "'").replace("&quot;", '"')
    if "-" in seg:
        seg = _YEARS.sub("\\1\u2013\\2", seg)
        seg = _SPACED.sub(" \u2013 ", seg)
    if " " in seg and ("%" in seg or any(w in seg for w in ("Table ", "Figure ", "Tabla ", "Figura ", "Section ", "Sección ", "Part", "page", "página"))):
        seg = _NBSP_WORD.sub("\\1\u00a0\\2", seg)
        seg = _NBSP_PCT.sub("\\1\u00a0%", seg)
    if "'" in seg or '"' in seg:
        s = prev + seg
        s = _APOS_IN.sub("\u2019", s)
        s = _APOS_DECADE.sub("\u2019", s)
        s = _OPEN_S.sub("\u2018", s)
        s = s.replace("'", "\u2019")
        s = _OPEN_D.sub("\u201c", s)
        s = s.replace('"', "\u201d")
        seg = s[len(prev):]
    return seg


def typeset(html: str) -> str:
    parts = _SPLIT.split(html)
    out, skip, prev = [], None, " "
    for k, part in enumerate(parts):
        if k % 2:  # a tag
            if skip:
                if part[:2] == "</" and part[2:2 + len(skip)].lower() == skip:
                    skip = None
            else:
                m = _SKIP_OPEN.match(part)
                if m:
                    skip = m.group(1).lower()
                elif _BLOCK.match(part):
                    prev = " "
            out.append(part)
        elif skip or not part:
            out.append(part)
        else:
            t = _text(part, prev)
            out.append(t)
            prev = t[-1]
    return "".join(out)
