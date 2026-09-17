"""
extract_commitments.py
-----------------------
This is the "extraction agent" behind the Daily Brief prototype.

It reads the raw, messy inputs (meeting transcript, calendars, email threads,
voice memo transcripts) from data/raw_input.txt and uses Claude to turn them
into the structured commitments schema that index.html renders and reasons
over (my_action / waiting_on / flag, deadlines, dedup, source trail).

The UI itself (index.html) ships with this output already baked in, so the
prototype works offline with zero setup. Run this script only if you want to
see/regenerate that extraction step yourself, or point it at a different
week's data pack.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install anthropic
    python extract_commitments.py
    -> writes commitments.generated.json
"""

import json
import os
import sys

import anthropic

SCHEMA_INSTRUCTIONS = """
You are the extraction stage of an executive productivity agent. You are given
messy raw inputs for one VP (Arjun Malhotra): a meeting transcript, calendars
for several people, several email threads, and personal voice-memo transcripts.

Turn these into a JSON array of COMMITMENTS. A commitment is any promise,
deliverable, or open item involving Arjun — either something he owes someone
else, or something someone else owes him, or an item where ownership is
genuinely unclear from the text.

Rules (follow these exactly):
1. DEDUPE. The same commitment is often mentioned multiple times across the
   meeting, an email thread, and a voice memo (e.g. a deadline gets pushed
   twice). Merge all mentions of the same underlying commitment into ONE
   object. Use the *most recent* mention to set the current deadline and
   resolution status. List every mention in "sources", oldest first.
2. DIRECTION. Set "direction" to:
   - "my_action" if Arjun is the one who made the promise
   - "waiting_on" if someone else promised something to Arjun
   - "flag" if the text shows real ambiguity about who owns it — never guess
     an owner the text doesn't name. If Facilities, Raghav, and Divya are all
     unsure who owns something, direction is "flag" and counterpart is
     "Unassigned".
3. DO NOT INVENT. Only use information present in the raw text. If a deadline,
   owner, or resolution isn't stated or clearly implied, leave it null rather
   than guessing.
4. STALE REMINDERS. If a voice memo or later message restates a commitment
   that was already resolved by an earlier-timestamped source in a different
   channel, still record it, but set "stale_reminder": true on that specific
   source entry, since the agent should not reopen something already closed.
5. CALENDAR CONFLICTS. If two calendar entries for Arjun himself overlap in
   time (e.g. a meeting he must attend overlaps another commitment's
   deadline/meeting time), add a top-level "conflict_note" field on the
   relevant commitment describing the overlap.

Output STRICT JSON only — an array of objects, no prose, no markdown fences.
Each object shape:
{
  "id": "kebab-case-id",
  "title": "short imperative description",
  "direction": "my_action" | "waiting_on" | "flag",
  "counterpart": "name or 'Unassigned'",
  "deadline": "ISO 8601 datetime or null",
  "deadline_label": "human readable, e.g. 'Wed 23 Sep, evening'",
  "resolved_at": "ISO 8601 datetime or null",
  "conflict_note": "string or null",
  "note": "1-2 sentence summary of the situation, for a VP skimming a brief",
  "sources": [
    {"t": "ISO 8601 datetime", "type": "Meeting|Email|Voice memo|Calendar",
     "label": "e.g. '\"Vendor List\" thread'", "text": "paraphrased summary of that message",
     "stale_reminder": false}
  ]
}
"""


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY before running this script.")

    with open(os.path.join(os.path.dirname(__file__), "data", "raw_input.txt")) as f:
        raw_data = f.read()

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SCHEMA_INSTRUCTIONS,
        messages=[{"role": "user", "content": raw_data}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        commitments = json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"Model did not return valid JSON: {e}\n\nRaw output:\n{text}")

    out_path = os.path.join(os.path.dirname(__file__), "commitments.generated.json")
    with open(out_path, "w") as f:
        json.dump(commitments, f, indent=2)

    print(f"Extracted {len(commitments)} commitments -> {out_path}")


if __name__ == "__main__":
    main()
