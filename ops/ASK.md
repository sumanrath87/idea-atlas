# Improving the "Ask a question" box

The box answers in the visitor's browser from `data/values.json` and `data/guides_<lang>.json`. It never guesses: an answer
is either an atlas figure, a guide section, or a suggestion to rephrase. The words it understands live in `QA` near the
top of the ask section of `build/assets/atlas.js`.

## What it collects

- `ask/answered/<kind>`: the kind of answer shown (district, compare, state, nation, guides, definition, choose, nomatch). No question text.
- `ask/helpful/<kind>` and `ask/not-helpful/<kind>`: the visitor's Yes or No. No question text.
- `ask/question/<kind>/<lang>`: only when the visitor presses "Send this question". The question (emails, phone numbers and
  long numbers removed, first 200 characters) is the event title.

All of these are GoatCounter events, visible only on the private dashboard (sumanrath.goatcounter.com), under Pages with
event names starting with `ask/`.

## Monthly review (about 20 minutes)

1. Open the dashboard, filter to `ask/question`, and read the sent questions. Note the share of `not-helpful` answers by kind.
2. For each missed question, add what was missing to `QA` in `build/assets/atlas.js`: a phrase for a topic (`topics`),
   a phrase that points to a guide (`guideHints`), a definition trigger (`definitions`), or a common word that must not
   be read as a district name (`generic` / `stop`).
3. Add the question to `ops/ask_questions.json` so it stays answered in future.
4. Build locally (`ATLAS_FAST=1 python build/site.py`), serve `site/`, and run `python ops/ask_test.py`. Read every answer.
5. Commit and push; the site rebuilds and publishes.

Never paste a sent question into the code if it contains anything that could identify a child or family.
