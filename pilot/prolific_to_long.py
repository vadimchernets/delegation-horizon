#!/usr/bin/env python3
"""prolific_to_long.py: turn Prolific Survey Builder exports into the input of human_raters.py.

Mechanical conversion only; every rule of the analysis lives in human_raters.py, registered
before data collection (OSF 10.17605/OSF.IO/V92R8).
- rater: a plain label R001, R002, ... given in a random order drawn from the system's random source,
  so the labels say nothing about the IDs. Neither the ID nor any hash of it is written, and the order of
  the labels does not follow the salted hashes (the salt below is public), so the file can be published as
  it is: nobody holding an ID can find that person's rows (--relabel is still accepted and changes nothing);
- task_id: from the question text "Task BK01: ..."; the repeated task "Task BK03 (again): ..."
  becomes "BK03-retest";
- reference_hours: the one number written in the answer, read as written in the six English-speaking
  countries sampled (".5" and ",5" are 0.5, "1,200" is 1200, "1,5" is 1.5), divided by 60 for minutes.
  The unit is the one written in the answer when it names one ("90 min" is 1.5 hours whatever the
  selector says), otherwise the selector's, read in any case ("Minutes", "mins"). An answer with no
  number, with more than one ("8-12", "3 hrs 30 min"), with a minus sign, with a numeral other than 0 to 9
  ("1\u00bd"), or in days, weeks or months is kept as text, and human_raters.py drops it as not a positive
  number, as registered; text that Python would still read as a number ("1e3", "1_500", "inf") is
  written with the prefix "text: " so that it is dropped too. Every answer that is not a plain number is
  counted on the screen and listed with --report, with what it became;
- attention_ok: 1 if the attention question was answered "Twelve";
- competency_ok: 1 if the competency question got its correct option;
- competency_answer: the option the participant chose in the competency question (empty if none), so
  the wrong answers can be counted (Appendix G2: eight of the 11 reversed the debit and the credit).
Usage: python3 pilot/prolific_to_long.py out.csv bookkeeping=BK/responses.jsonl webtools=WT/responses.jsonl
       [--report]
Licence: MIT
"""
import argparse
import csv
import hashlib
import json
import random
import re
import sys

CORRECT = {
    "double-entry": "Debit bank, credit accounts receivable",
    "LEFT JOIN": "All rows of the left table, with matching rows of the right table or NULLs",
}
SALT = "delegation-horizon-prepilot-2026-10-09"
PLAIN = re.compile(r"\d+(?:\.\d+)?")
# one number as written: thousands with commas (1,200.5), a decimal with or without a leading digit (.5, 2.5),
# or digits with a decimal comma of one or two places (1,5)
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d*\.\d+|\d+(?:,\d{1,2}(?!\d))?|(?<![\d.,]),\d{1,2}(?!\d)")
# a unit named in the answer itself: hours or minutes are applied, a longer unit leaves the answer as text
WRITTEN = re.compile(r"(?i)(?<![a-z])(hours?|hrs?|h|minutes?|mins?|days?|weeks?|months?)(?![a-z])")
FACTOR = {"hour": 1.0, "hours": 1.0, "hr": 1.0, "hrs": 1.0, "h": 1.0,
          "minute": 1 / 60, "minutes": 1 / 60, "min": 1 / 60, "mins": 1 / 60}


def number(text):
    """The one number written in an answer, or None when it holds no number, more than one, a minus sign before it
    or a numeral other than 0 to 9."""
    text = str(text) if text is not None else ""
    if any(ch.isnumeric() and ch not in "0123456789" for ch in text):
        return None
    found = list(NUMBER.finditer(text))
    if len(found) != 1:
        return None
    start = found[0].start()
    if start and text[start - 1] in "-\u2212":
        return None
    token = found[0].group(0)
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", token):
        return float(token.replace(",", ""))
    return float(token.replace(",", "."))


def hours(raw, unit):
    """The estimate in hours, or the answer kept as text so that human_raters.py drops it."""
    n = number(raw)
    written = {w.lower() for w in WRITTEN.findall(raw)}
    if n is not None and written and written <= set(FACTOR):
        factors = {FACTOR[w] for w in written}
        if len(factors) == 1:
            return n * factors.pop()
    elif n is not None and not written and str(unit).strip().lower() in FACTOR:
        return n * FACTOR[str(unit).strip().lower()]
    try:
        float(raw)
    except ValueError:
        return raw
    return "text: " + raw                      # Python would read it as a number; the prefix makes sure it is dropped


def convert(domain, path, notes=None):
    rows = []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        rater = hashlib.sha256((SALT + r["participant_id"]).encode()).hexdigest()[:10]
        att = comp = "0"
        answer = ""
        estimates = []
        for q in r["responses"].values():
            d = q.get("description", "")
            if q["type"] == "multiple_choice":
                v = (q.get("values") or [""])[0]
                if d.startswith("Attention check"):
                    att = "1" if v == "Twelve" else "0"
                for key, right in CORRECT.items():
                    if key in d:
                        comp = "1" if v == right else "0"
                        answer = v
            elif q["type"] == "free_text_with_unit":
                m = re.match(r"Task (\w\w\d\d)( \(again\))?:", d)
                if not m:
                    continue
                task = m.group(1) + ("-retest" if m.group(2) else "")
                raw = str(q.get("value", "")).strip()
                h = hours(raw, q.get("unit", ""))
                if notes is not None and not PLAIN.fullmatch(raw):
                    notes.append((domain, rater, task, raw, q.get("unit", ""), h))
                estimates.append((task, h))
        for task, h in estimates:
            rows.append({"domain": domain, "rater": rater, "task_id": task, "reference_hours": h,
                         "attention_ok": att, "competency_ok": comp, "competency_answer": answer})
    return rows


def relabel(rows, rng=None):
    """Replace each salted hash by R001, R002, ... in a random order: in the order of the hashes, anyone holding an ID
    and the public salt could estimate that person's label."""
    hashes = sorted({r["rater"] for r in rows})
    (rng or random.SystemRandom()).shuffle(hashes)
    names = {h: f"R{i:03d}" for i, h in enumerate(hashes, 1)}
    for r in rows:
        r["rater"] = names[r["rater"]]
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description="Turn Prolific Survey Builder exports into the input of human_raters.py.")
    ap.add_argument("out", help="long CSV to write")
    ap.add_argument("sources", nargs="+", metavar="domain=responses.jsonl")
    ap.add_argument("--relabel", action="store_true",
                    help="accepted for older command lines; labels are always plain (R001, ...)")
    ap.add_argument("--report", action="store_true", help="list every answer that is not a plain number")
    args = ap.parse_args(argv)
    rows, notes = [], []
    for arg in args.sources:
        if "=" not in arg:
            ap.error(f"write each export as domain=path, for example bookkeeping=BK/responses.jsonl; got {arg!r}")
        domain, path = arg.split("=", 1)
        try:
            rows += convert(domain, path, notes)
        except OSError as err:
            sys.exit(f"{path}: {err.strerror}")
        except (ValueError, KeyError, TypeError, AttributeError) as err:
            sys.exit(f"{path}: not a Prolific Survey Builder export of one JSON object per line ({err})")
    names = relabel(rows)                          # never write a hash: the salt above is public
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["domain", "rater", "task_id", "reference_hours", "attention_ok",
                                           "competency_ok", "competency_answer"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows, {len({(r['domain'], r['rater']) for r in rows})} participants -> {args.out}")
    print(f"{len(notes)} answers were not a plain number" + ("" if args.report or not notes else " (--report lists them)"))
    if args.report:
        for domain, rater, task, raw, unit, h in notes:
            became = f"{h:g} hours" if isinstance(h, float) else "kept as text: dropped by human_raters.py"
            print(f"  {domain} {names.get(rater, rater)} {task}: {raw!r} {unit} -> {became}")


if __name__ == "__main__":
    main()
