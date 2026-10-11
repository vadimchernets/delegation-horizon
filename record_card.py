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
import io
import json
import math
import os
import re
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
DATES = ("started", "date")


def spreadsheet_date(text):
    """A date as a spreadsheet saved it: 2026-09-14 stays, 14.09.2026 (day first, as European spreadsheets write it)
    becomes 2026-09-14. Anything else, such as 9/14/2026, whose day and month cannot be told apart, gives None."""
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        text = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def read_text(path):
    """The file as text: UTF-8 with or without a BOM, or Windows-1252, the code page spreadsheets on Windows save
    CSV in."""
    with open(path, "rb") as fh:
        raw = fh.read()
    for codec in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(codec)
        except UnicodeDecodeError:
            continue
    sys.exit(f"{path}: the file is neither UTF-8 nor Windows-1252 text; save it again as CSV UTF-8")


class AmbiguousNumber(ValueError):
    """A number such as 1.030, which one spreadsheet writes for a thousand and thirty and another for 1.03."""


def semicolon_number(text):
    """In a file saved with semicolons, 8,5 is eight and a half and 1.030,5 is a thousand and thirty and a half; any
    other dot is a decimal point (8.5, 0.125). A number such as 1.030 or 8.125 with no comma is a thousand and thirty
    in a German spreadsheet and one point zero three in a Swiss one, so it is refused, never guessed."""
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+,\d+", text):
        return text.replace(".", "").replace(",", ".")
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+", text):
        raise AmbiguousNumber(text)
    return text.replace(",", ".")


PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def finite(text):
    """float(text) for a number written plainly in the digits 0 to 9 (as checker.html reads it) and finite: nan, inf,
    1e999, 1_000, 0x10 and digits of other scripts raise ValueError like any other non-number."""
    if not PLAIN_NUMBER.fullmatch(text):
        raise ValueError(text)
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(text)
    return value


def iso_date(text):
    """--as-of: a date written YYYY-MM-DD, or a message from argparse instead of a traceback."""
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a date written YYYY-MM-DD, got {text!r}") from None


THOUSANDS = "must be written without a dot between thousands (1030) or with a decimal comma (1,03)"


def csv_rows(path):
    """(record, physical line) for each row of the spreadsheet template: the same columns as the JSON log. Blank
    lines before the header are skipped. A file saved with semicolons (as spreadsheets set to a European language
    save CSV) is read with semicolons, decimal commas and dots between thousands. checker.html reads it the same way."""
    text = read_text(path)
    lead = re.match(r"(?:[ \t]*(?:\r\n|\r|\n))*", text).group(0)
    first = len(re.findall(r"\r\n|\r|\n", lead))            # blank lines before the header
    body = text[len(lead):]
    header = re.split(r"\r\n|\r|\n", body, maxsplit=1)[0]
    semicolon = header.count(";") > header.count(",")
    reader = csv.reader(io.StringIO(body, newline=""), delimiter=";" if semicolon else ",")
    head = [h.strip() for h in next(reader, [])]
    out = []
    for cells in reader:
        n = first + reader.line_num                            # the physical line the row ends on
        row = {h: (cells[j] if j < len(cells) else "").strip() for j, h in enumerate(head) if h}
        if not any(row.values()):
            continue
        for key in horizon.OPTIONAL:                           # an empty optional cell is no field
            if not row.get(key):
                row.pop(key, None)
        for key in DATES:
            if key in row:
                iso = spreadsheet_date(row[key])
                if iso is None:
                    sys.exit(f"row {n}: {key} must be a date written YYYY-MM-DD (or DD.MM.YYYY), got {row[key]!r}; "
                             "set the column to text in the spreadsheet and type the date as 2026-09-14")
                row[key] = iso
        if "rater_hours" in row:                               # "6;10" in a spreadsheet cell
            cell = row["rater_hours"]
            parts = cell.split(";") if semicolon else cell.replace(",", ";").split(";")
            try:
                row["rater_hours"] = [finite(semicolon_number(x.strip()) if semicolon else x.strip()) for x in parts
                                      if x.strip()]
            except AmbiguousNumber:
                sys.exit(f"row {n}: rater_hours {THOUSANDS}, got {cell!r}")
            except ValueError:
                sys.exit(f"row {n}: rater_hours must be numbers separated by ';', got {cell!r}")
        for key, kind in NUMBERS.items():
            if key in row:
                try:
                    value = finite(semicolon_number(row[key]) if semicolon else row[key])
                    row[key] = int(value) if kind is int or value.is_integer() else value
                except AmbiguousNumber:
                    sys.exit(f"row {n}: {key} {THOUSANDS}, got {row[key]!r}")
                except (ValueError, OverflowError):
                    sys.exit(f"row {n}: {key} must be a number, got {row[key]!r}")
        for key in FLAGS:
            if key in row:
                word = row[key].lower()
                if word not in TRUE | FALSE:
                    sys.exit(f"row {n}: {key} must be yes or no, got {row[key]!r}")
                row[key] = word in TRUE
        out.append((row, n))
    return out


def csv_to_records(path):
    """Read the spreadsheet template: one record per row (see csv_rows)."""
    return [row for row, _ in csv_rows(path)]


def jsonl_lines(path):
    """The lines of a JSON Lines log, each checked for JSON and for dates written YYYY-MM-DD, so a mistake is named
    with its line instead of stopping with a traceback; a BOM is dropped. Physical line numbers are kept."""
    text = read_text(path)
    for n, line in enumerate(re.split(r"\r\n|\r|\n", text), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            sys.exit(f"line {n}: not valid JSON")
        for key in DATES:
            if isinstance(r, dict) and key in r and spreadsheet_date(str(r[key])) != r[key]:
                sys.exit(f"line {n}: {key} {r[key]!r} is not a date written YYYY-MM-DD")
        for key in sorted(FLAGS):                  # horizon.py reads "no" as true; say so before it scores
            if isinstance(r, dict) and key in r and not isinstance(r[key], bool):
                sys.exit(f"line {n}: {key} must be true or false, without quotes, got {r[key]!r}")
    return text


def load_any(path):
    """Validate through horizon.load, so a CSV log obeys exactly the rules of a JSON log. A rule horizon.load names
    by its line is reported with the row of the spreadsheet it came from."""
    fd, tmp = tempfile.mkstemp(suffix=".jsonl")
    try:
        if not path.lower().endswith(".csv"):
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(jsonl_lines(path))
            return horizon.load(tmp)
        rows = csv_rows(path)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for r, _ in rows:
                fh.write(json.dumps(r) + "\n")
        try:
            return horizon.load(tmp)
        except SystemExit as stop:
            m = re.match(r"line (\d+): (.*)", str(stop.code), re.S)
            if m and 0 < int(m.group(1)) <= len(rows):
                sys.exit(f"row {rows[int(m.group(1)) - 1][1]}: {m.group(2)}")
            raise
    finally:
        os.remove(tmp)


def pretty_step(s):
    return s.replace("x", "×")


def passes_needed(n):
    """The fewest verified pieces out of n that meet the pass share, by the comparison horizon.py makes."""
    return next((k for k in range(n + 1) if n and k / n >= horizon.PASS_SHARE), 0)


def needed_note(rung, n):
    """What the rung asks of n pieces of its size: the verified ones needed, or the pieces too when n is short."""
    minimum = next(r[2] for r in horizon.RUNGS if r[0] == rung)
    if n < minimum:
        return f"{minimum} pieces and {passes_needed(minimum)} verified needed"
    return f"{passes_needed(n)} needed"


def below_hour_note(counted):
    """Why Hour is not earned when the count of Hour-size pieces would meet it: an irreversible piece not verified."""
    minimum = next(r[2] for r in horizon.RUNGS if r[0] == "Hour")
    v, n = sum(map(horizon.verified, counted)), len(counted)
    if n >= minimum and v >= passes_needed(n) and any(r["irreversible"] and not horizon.verified(r) for r in counted):
        return "Hour not earned: an irreversible piece is not verified (every irreversible piece must pass)"
    return f"Hour not earned: {needed_note('Hour', n)}"


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
        counted = horizon.rung_pieces(pieces, rung, as_of)
        sized, _, _, window = next(r for r in horizon.RUNGS if r[0] == rung or (rung == "below Hour" and r[0] == "Hour"))
        out.append({
            "person": person, "domain": domain, "rung": rung, "size": SIZES[rung],
            "count": (sum(map(horizon.verified, counted)), len(counted), sized, window,
                      below_hour_note(counted) if rung == "below Hour" else needed_note(sized, len(counted))),
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
    verified, total, sized, window, needed = s["count"]
    return [
        ("Horizon", f"{s['rung']} ({s['size']}), scored by the rule of Section 5.2"),
        ("Count behind the rung", f"{verified} of {total} pieces of {sized} size verified in its {window}-day window "
                                  f"({needed})"),
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
    ap.add_argument("--as-of", type=iso_date, default=dt.date.today())
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
    as_of = args.as_of
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
