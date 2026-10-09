#!/usr/bin/env python3
"""record_card.py: turn a work log into the dated record and a card for a resume or an HR file.

Teaches: the record of Section 5.3, "domain . horizon . amplification . date", and what has to travel
with it to be read fairly (the kinds of check, the median verified size, failures kept in the count).
It reads the JSON Lines log of Appendix C1 or the spreadsheet template in templates/ (CSV), and scores
it with horizon.py unchanged, so the numbers are the paper's numbers.
Limits: it trusts the fields it is given, exactly as horizon.py does. A card is a summary of a log; the
log itself is the evidence, and a reader who wants to check the record should ask for it.
Usage:
  python3 record_card.py examples/c4-log.jsonl --as-of 2026-10-09
  python3 record_card.py my-log.csv --format md --out card.md
  python3 record_card.py my-log.csv --format json > record.json   (export-record.schema.json)
  python3 record_card.py my-log.csv --to-jsonl my-log.jsonl        (convert only)
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import statistics
import sys
import tempfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import horizon  # noqa: E402  (the scorer of Appendix C2, byte for byte)

PAPER = ("Chernets, V. (2026). After the Programmer Divide: One Measure for People Who Build "
         "Through AI Agents. Working paper. https://github.com/vadimchernets/delegation-horizon")
SIZES = {"Quarter": "about 500 reference hours", "Month": "about 160 reference hours",
         "Week": "about 40 reference hours", "Day": "about 8 reference hours",
         "Hour": "about 1 reference hour", "below Hour": "no rung yet"}
TRUE, FALSE = {"true", "yes", "y", "1"}, {"false", "no", "n", "0"}
NUMBERS = {"reference_hours": float, "attention_minutes": float,
           "planted_errors": int, "planted_missed": int}
FLAGS = {"agent_saw_check", "passed", "irreversible", "outside_help", "revoked"}


def csv_to_records(path):
    """Read the spreadsheet template: one row per piece, the same columns as the JSON log."""
    records = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for n, row in enumerate(csv.DictReader(fh), 2):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k and k.strip()}
            if not any(row.values()):
                continue
            for key in horizon.OPTIONAL:                 # an empty optional cell is no field
                if not row.get(key):
                    row.pop(key, None)
            if "rater_hours" in row:                     # "6;10" in a spreadsheet cell
                try:
                    row["rater_hours"] = [float(x) for x in row["rater_hours"].replace(",", ";").split(";") if x.strip()]
                except ValueError:
                    sys.exit(f"row {n}: rater_hours must be numbers separated by ';', got {row['rater_hours']!r}")
            for key, kind in NUMBERS.items():
                if key in row:
                    try:
                        value = float(row[key])
                    except ValueError:
                        sys.exit(f"row {n}: {key} must be a number, got {row[key]!r}")
                    row[key] = int(value) if kind is int or value.is_integer() else value
            for key in FLAGS:
                if key in row:
                    word = row[key].lower()
                    if word not in TRUE | FALSE:
                        sys.exit(f"row {n}: {key} must be yes or no, got {row[key]!r}")
                    row[key] = word in TRUE
            records.append(row)
    return records


def load_any(path):
    """Validate through horizon.load, so a CSV log obeys exactly the rules of a JSON log."""
    if not path.lower().endswith(".csv"):
        return horizon.load(path)
    fd, tmp = tempfile.mkstemp(suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for r in csv_to_records(path):
                fh.write(json.dumps(r) + "\n")
        return horizon.load(tmp)
    finally:
        os.remove(tmp)


def pretty_step(s):
    return s.replace("x", "×")


def summarise(records, as_of):
    """Group as horizon.main does and compute every number the card shows."""
    longest = max(days for *_, days in horizon.RUNGS)
    groups = defaultdict(list)
    for r in records:
        if as_of - dt.timedelta(days=longest) < r["date"] <= as_of:
            groups[(r["person"], r["domain"])].append(r)
    quarter = f"{as_of.year}-Q{(as_of.month - 1) // 3 + 1}"
    recent_start = as_of - dt.timedelta(days=horizon.GAIN_WINDOW)
    out = []
    for (person, domain), pieces in sorted(groups.items()):
        recent = [r for r in pieces if r["date"] > recent_start]
        good = [r for r in recent if horizon.verified(r)]
        g = horizon.gain(recent)
        rung = horizon.horizon(pieces, as_of)
        out.append({
            "person": person, "domain": domain, "rung": rung, "size": SIZES[rung],
            "step": pretty_step(horizon.step(g)), "gain": g, "quarter": quarter, "as_of": as_of,
            "pieces": len(recent), "verified": len(good), "not_verified": len(recent) - len(good),
            "checks": sorted({r["check"] for r in good}),
            "median_size": statistics.median(float(r["reference_hours"]) for r in good) if good else None,
            "irreversible": sum(1 for r in recent if r["irreversible"]),
            "planted": sum(1 for r in recent if int(r["planted_errors"]) > 0),
            "outside_help": sum(1 for r in recent if r["outside_help"]),
            "directive": (sum(r["mode"] == "one_piece" for r in recent) / len(recent)) if recent else 0.0,
            "attention_hours": sum(float(r["attention_minutes"]) for r in recent) / 60.0,
            "verified_hours": sum(float(r["reference_hours"]) for r in good if not r["outside_help"]),
        })
    return out


def record_line(s):
    return f"{s['domain']} · {s['rung']} · {s['step']} · {s['quarter']}"


def facts(s):
    gain = "n/a" if s["gain"] is None else f"{s['gain']:.2f}"
    median = "n/a" if s["median_size"] is None else f"{s['median_size']:g} reference hours"
    return [
        ("Horizon", f"{s['rung']} ({s['size']}), scored by the rule of Section 5.2"),
        ("Amplification", f"{s['step']} (gain {gain}: {s['verified_hours']:g} verified reference hours "
                          f"for {s['attention_hours']:.1f} hours of attention, failures included)"),
        ("Pieces, last 91 days", f"{s['pieces']} logged, {s['verified']} verified, "
                                 f"{s['not_verified']} not verified (kept in the count)"),
        ("Kinds of check", ", ".join(s["checks"]) or "none independent"),
        ("Median verified size", median),
        ("Irreversible pieces", str(s["irreversible"])),
        ("Pieces with planted errors", str(s["planted"])),
        ("Pieces with outside help", f"{s['outside_help']} (excluded from gain)"),
        ("Directive share", f"{s['directive']:.0%} handed over in one piece"),
        ("Scored on", s["as_of"].isoformat()),
    ]


def card_txt(s):
    lines = [record_line(s), "", f"Person: {s['person']}"]
    lines += [f"{k}: {v}" for k, v in facts(s)]
    lines += ["", "The log behind this record is available on request. The rung holds for this domain only,",
              "and it is confirmed again every quarter.", f"Measure: {PAPER}"]
    return "\n".join(lines) + "\n"


def card_md(s):
    lines = [f"### {record_line(s)}", "", f"*Person: {s['person']}*", "", "| | |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in facts(s)]
    lines += ["", "The log behind this record is available on request. The rung holds for this domain only, "
              "and it is confirmed again every quarter.", "", f"Measure: {PAPER}"]
    return "\n".join(lines) + "\n"


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def export(s, log_hash, scorer_hash):
    """The portable record of export-record.schema.json (Section 10.3)."""
    return {"format": "delegation-horizon-record/1", "person": s["person"], "domain": s["domain"],
            "rung": s["rung"], "gain_step": s["step"].replace("\u00d7", "x"),
            "gain": None if s["gain"] is None else round(s["gain"], 4), "quarter": s["quarter"],
            "as_of": s["as_of"].isoformat(), "pieces": s["pieces"], "verified": s["verified"],
            "not_verified": s["not_verified"], "checks": s["checks"],
            "median_verified_hours": s["median_size"], "irreversible": s["irreversible"],
            "planted": s["planted"], "outside_help": s["outside_help"],
            "directive_share": round(s["directive"], 4), "attention_hours": round(s["attention_hours"], 4),
            "verified_hours": s["verified_hours"], "scorer": {"name": "horizon.py", "sha256": scorer_hash},
            "log_sha256": log_hash}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log", help="work log: .jsonl (Appendix C1) or .csv (templates/work-log.csv)")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--format", choices=["record", "txt", "md", "json"], default="txt",
                    help="json: one portable record per line (export-record.schema.json)")
    ap.add_argument("--person", help="only this pseudonymous label")
    ap.add_argument("--out", help="write here instead of the screen")
    ap.add_argument("--to-jsonl", metavar="PATH", help="only convert a CSV log to JSON Lines and stop")
    args = ap.parse_args(argv)
    if args.to_jsonl:
        rows = csv_to_records(args.log) if args.log.lower().endswith(".csv") else None
        if rows is None:
            sys.exit("--to-jsonl needs a .csv log")
        with open(args.to_jsonl, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        horizon.load(args.to_jsonl)          # the converted log must pass the scorer's checks
        print(f"wrote {len(rows)} lines to {args.to_jsonl}")
        return
    as_of = dt.date.fromisoformat(args.as_of)
    found = [s for s in summarise(load_any(args.log), as_of)
             if args.person is None or s["person"] == args.person]
    log_hash, scorer_hash = sha256(args.log), sha256(horizon.__file__)
    render = {"record": lambda s: record_line(s) + "\n", "txt": card_txt, "md": card_md,
              "json": lambda s: json.dumps(export(s, log_hash, scorer_hash)) + "\n"}[args.format]
    sep = "" if args.format in ("record", "json") else "\n"
    text = sep.join(render(s) for s in found) or "no pieces in the window\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
