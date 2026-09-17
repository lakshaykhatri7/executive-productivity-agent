# Executive Productivity Agent — Daily Brief

A prototype agent that turns an executive's messy week (meeting transcript,
emails, calendars, voice memos) into a single daily action brief — built for
the AIONOS Agentic AI Factory assignment.

**Live prototype:** open `index.html` directly in a browser, or enable
GitHub Pages on this repo for a shareable link (Settings → Pages → deploy
from `main` / root).

## The problem

Arjun Malhotra (VP Sales) makes and receives commitments across four
channels — a leadership sync, five email threads, five people's calendars,
and two voice memos to himself. The same commitment often shows up more than
once, with the deadline quietly changing each time. The agent's job is to
turn that mess into one trustworthy answer to "what do I actually need to do
today," without inventing anything the source material doesn't say.

## Architecture

```mermaid
flowchart LR
    subgraph Sources
        A[Meeting transcript]
        B[Email threads x5]
        C[Calendars x5]
        D[Voice memos x2]
    end

    A & B & C & D --> E[Extraction agent<br/>extract_commitments.py<br/>Claude Sonnet]
    E -->|structured JSON| F[(Commitments schema<br/>direction, deadline,<br/>sources, resolution)]
    F --> G[Reasoning layer<br/>dedup · overdue detection ·<br/>ownership flagging ·<br/>calendar-conflict check ·<br/>stale-reminder check]
    G --> H[Daily Brief UI<br/>index.html]
    G --> I[Q&A over commitments<br/>e.g. \"What did I promise Raghav?\"]
```

Two stages, deliberately kept separate:

1. **Extraction** (`extract_commitments.py`) — an LLM call that reads the raw
   text and produces one structured commitment per underlying promise,
   already deduplicated and already carrying a `direction` (`my_action` /
   `waiting_on` / `flag`). This is the only stage that needs an LLM; it runs
   once per data refresh, not on every page view.
2. **Reasoning + UI** (`index.html`) — deterministic, auditable logic over
   that structured output: compare each deadline to "now," detect calendar
   overlaps, and never assign an owner the flag stage didn't confirm. This
   stage is intentionally rule-based rather than another LLM call, so every
   status shown in the brief can be traced back to a specific rule and a
   specific source line — important for something an executive is trusting
   with their commitments.

The shipped `index.html` embeds the extraction output directly (as the
`COMMITMENTS` array) so the demo works standalone with no API key and no
server. `extract_commitments.py` is included so the extraction step itself
is inspectable and re-runnable against a different week's data pack — see
"Regenerating the data" below.

## What the agent does

- **My actions vs. waiting on others** — split by who made the promise.
- **Deduplication** — the vendor list commitment alone is mentioned across
  1 meeting, 2 emails, and 1 voice memo with the deadline changing twice;
  it's shown as one card with a 6-entry source trail, not four to-dos.
- **Overdue detection** — tracked against the *latest* agreed deadline, not
  the first one mentioned.
- **Ownership flagging without invention** — the Mumbai lease sign-off is
  raised by three different people and never claimed by any of them; the
  agent surfaces it as an open flag rather than guessing an owner.
- **Calendar-conflict detection** — the Thursday deck review (9:30–10:00 AM)
  overlaps Arjun's own Board Prep Session (9:00–10:00 AM); flagged
  separately since it's a scheduling problem, not just a tight deadline.
- **Stale-reminder detection** — Arjun's Wednesday morning voice memo asks
  himself to "lock in a time" with Priya that was, per the email thread,
  already confirmed the evening before. The agent treats this as a stale,
  already-resolved note rather than reopening a closed item.
- **A timeline scrubber** ("Viewing as of") so the brief can be replayed at
  any point across the week — useful for testing that overdue/resolved
  states change correctly over time, and for a reviewer to see the logic
  work without waiting for the actual week to happen.
- **Ask-a-question box** — free-text and quick-chip questions like "What did
  I promise Raghav?" or "What's unresolved?", answered by filtering the same
  structured commitments the brief is built from.

## Inputs, sources, and assumptions

| Source | Used for |
|---|---|
| Leadership sync transcript (Mon 9:00 AM) | Origin point for 4 of the 6 tracked commitments |
| 5 email threads | Deadline revisions and resolutions |
| 5 calendars (Arjun, Neha, Raghav, Divya) | Confirming scheduled meetings and detecting the deck-review/board-prep conflict |
| 2 voice memos | Arjun's own commitments to himself; treated as a source of truth about his intent, not as instructions from a third party |

Assumptions made explicit rather than silently baked in:
- All timestamps are read literally from the data pack (week of 21–25 Sep
  2026); "today," "tomorrow," and "this morning" are resolved against the
  date the message was sent, not the date it's read.
- When a deadline is restated with a new time, the **most recent** mention
  wins — earlier ones are kept only in the source trail for context.
- An item is only marked `flag` (unclear ownership) when the text itself
  shows disagreement or non-assignment — never as a default for "no deadline
  given."
- Facilities' broadcast emails are treated as a source, not as a commitment
  owner — a mailing list can't "own" a task.

## AI tools used and how

- **Claude (Sonnet)**, via `extract_commitments.py`, is used as the
  extraction stage described above: reading raw transcript/email/calendar
  text and producing the structured commitments JSON the rest of the app
  consumes. The prompt (see `SCHEMA_INSTRUCTIONS` in that file) explicitly
  encodes the dedup, no-invention, and ownership-flagging rules so the model
  applies them consistently.
- **Claude**, via this chat interface, was used to build the prototype
  itself (HTML/CSS/JS) and this README, working from the assignment's data
  pack.
- No other AI tools were used.

## Running it

**View the prototype (no setup):**
```
open index.html
```
or serve the folder and enable GitHub Pages for a shareable link.

**Regenerate the extraction output from raw data (optional):**
```
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python extract_commitments.py
# writes commitments.generated.json
```
This reproduces (and lets you inspect/tweak) the structured data that's
already embedded in `index.html`. Swap `data/raw_input.txt` for a different
week's inputs to see the same pipeline run on new data.

## Repo structure

```
index.html                    the prototype (open this)
extract_commitments.py        LLM extraction agent (Claude Sonnet)
data/raw_input.txt            raw data pack fed to the extraction agent
commitments.generated.json    output of extract_commitments.py (generated, not committed by default)
README.md                     this file
```
