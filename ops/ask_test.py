"""Run every question in ops/ask_questions.json against a local build (python -m http.server 8765 in site/) and print the answers.
Needs: pip install playwright, and a Chrome or Chromium."""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

QS = json.loads((Path(__file__).parent / "ask_questions.json").read_text())
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
JS = """() => Array.from(document.querySelectorAll('#qa-out h4, #qa-out .qa-note, #qa-out li, #qa-out td')).slice(0, 10)
          .map(e => e.textContent.replace(/\\s+/g, ' ').slice(0, 110)).join(' | ')"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        pg = await b.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        for lang, path in (("en", ""), ("es", "es/")):
            await pg.goto(URL + path)
            for q in QS[lang]:
                await pg.fill("#qa-q", q); await pg.click("#qa-form button[type=submit]")
                await pg.wait_for_selector("#qa-h", timeout=15000)
                print("Q:", q, "\n  ", (await pg.evaluate(JS))[:600])
                await pg.evaluate("document.querySelector('#qa-out').innerHTML = ''")
        print("Script errors:", errs or "none")
        await b.close()

asyncio.run(main())
