"""Each state's IDEA Part B SPP/APR (FFY 2024, published 2026) as PDF, from sites.ed.gov/idea. Newest year first."""
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent / "raw"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36 IDEA-Atlas/0.3"}
ST = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for s in ST:
        got = False
        for ffy in ("FFY24", "FFY2024", "FFY23", "FFY2023"):
            for name in (f"{s}-B-SPP-APR-{ffy}.pdf", f"{s}-B-SPPAPR-{ffy}.pdf", f"{s.lower()}-b-spp-apr-{ffy.lower()}.pdf"):
                u = f"https://sites.ed.gov/idea/files/{name}"
                try:
                    r = requests.get(u, headers=UA, timeout=120)
                    if r.ok and r.content[:4] == b"%PDF":
                        (RAW / f"apr_{s}_{ffy}.pdf").write_bytes(r.content)
                        print("ok", s, u, len(r.content))
                        got = True
                        break
                except Exception as e:
                    print("err", s, u, e)
            if got:
                break
        if not got:
            print("miss", s)
    import tarfile
    with tarfile.open(RAW / "apr_pdfs.tgz", "w:gz") as t:
        for f in sorted(RAW.glob("apr_*.pdf")):
            t.add(f, arcname=f.name)
            f.unlink()


if __name__ == "__main__":
    main()
