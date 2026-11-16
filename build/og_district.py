"""Share image for a district page: the district, its state, and up to four headline figures."""
from __future__ import annotations
from pathlib import Path

W, H = 1200, 630
BG, MAROON, INK, MUTED, RULE = "#faf6ee", "#26386b", "#1b2236", "#565c6b", "#e7dfcd"


def make(out: Path, *, name: str, place: str, figures: list[tuple[str, str]], footer: str, brand_note: str) -> None:
    """figures: up to four (number, label) pairs, e.g. ("18.0", "of every 100 students have an IEP")."""
    from PIL import Image, ImageDraw
    import extra_pages as xp
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 18, H], fill=MAROON)
    d.text((80, 58), "IDEA Atlas", font=xp._font("vollkorn", 40, 600), fill=MAROON)
    d.rectangle([80, 108, 124, 111], fill="#c98a1b")
    d.text((80 + d.textlength("IDEA Atlas", font=xp._font("vollkorn", 40, 600)) + 22, 72), brand_note, font=xp._font("manrope", 22, 400), fill=MUTED)
    tf = xp._font("vollkorn", 54 if len(name) < 38 else 46, 600)
    y = 128
    for ln in xp._wrap(d, name, tf, 1040)[:2]:
        d.text((80, y), ln, font=tf, fill=INK)
        y += 64
    d.text((80, y + 4), place, font=xp._font("manrope", 26, 600), fill=MUTED)
    top = max(y + 62, 300)
    d.line([80, top - 18, W - 80, top - 18], fill=RULE, width=2)
    nf, lf = xp._font("vollkorn", 64, 600), xp._font("manrope", 21, 400)
    colw = (W - 160) // 4
    for i, (num, lab) in enumerate(figures[:4]):
        x = 80 + i * colw
        d.text((x, top), num, font=nf, fill=INK, features=["lnum"])
        yy = top + 84
        for ln in xp._wrap(d, lab, lf, colw - 26)[:4]:
            d.text((x, yy), ln, font=lf, fill=MUTED)
            yy += 28
    d.text((80, 560), "atlas.sumanrath.org", font=xp._font("manrope", 23, 700), fill=INK)
    d.text((80 + d.textlength("atlas.sumanrath.org", font=xp._font("manrope", 23, 700)) + 24, 560), footer, font=xp._font("manrope", 23, 400), fill=MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    q = im.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:45] + [201, 138, 27]          # keep the saffron rule exact
    p_img = Image.new("P", (1, 1))
    p_img.putpalette(pal + [0] * (768 - len(pal)))
    im = im.quantize(palette=p_img, dither=Image.Dither.NONE)
    im.save(out, "PNG", optimize=True)
