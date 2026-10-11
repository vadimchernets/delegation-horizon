#!/usr/bin/env python3
"""verify_record.py: check a portable record against the log it says it comes from.

Teaches: the receiving side of Section 10.3 and of a gate that checks the work (Section 6.2). A card or a portable
record says what a log earned; the log is the evidence. Given the record (record_card.py --format json, one or more
lines, export-record.schema.json) and the log (JSON Lines or the spreadsheet template), this tool answers three
questions for each record: is this the log file that was scored (SHA-256), is this the scorer that scored it
(SHA-256 of horizon.py), and does rescoring the log on the record's date give the same record, field by field?
It prints MATCH, or every difference, and exits with 0 only when every record matches on all three.
Exit codes: 0 every record matches; 1 a difference was found; 2 the record or the log could not be read.
Limits: like horizon.py it trusts the fields of the log; whether the checks behind the log were independent is a
question for the audit (audit_sample.py, kits/audit-checklist.md).
Usage: python3 tools/verify_record.py record.json their-log.csv
Licence: MIT
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (the scorer of Appendix C2, byte for byte)
import record_card  # noqa: E402  (writes the portable record this tool reads)

SCHEMA = os.path.join(ROOT, "export-record.schema.json")
SHA = re.compile(r"^[0-9a-f]{64}$")


def read_records(path):
    """One record, a list of records, or one record per line (as record_card.py --format json writes them)."""
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    try:
        whole = json.loads(text)
        found = whole if isinstance(whole, list) else [whole]
    except ValueError:
        found = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    found.append(json.loads(line))
                except ValueError as err:
                    raise ValueError(f"line {n} of the record file is not JSON ({err.msg})") from None
    if not found:
        raise ValueError("the record file holds no record")
    return found


def schema_problems(rec, schema):
    """The checks of export-record.schema.json that matter for reading a record, with the standard library only."""
    if not isinstance(rec, dict):
        return ["a record must be a JSON object"]
    props, problems = schema["properties"], []
    missing, unknown = set(schema["required"]) - set(rec), set(rec) - set(props)
    if missing:
        problems.append("missing " + ", ".join(sorted(missing)))
    if unknown:
        problems.append("unknown " + ", ".join(sorted(unknown)))
    if missing:
        return problems
    if rec["format"] != props["format"]["const"]:
        problems.append(f"format must be {props['format']['const']}")
    for key in ("rung", "gain_step"):
        if rec[key] not in props[key]["enum"]:
            problems.append(f"{key} {rec[key]!r} is not one of the allowed values")
    if not isinstance(rec["checks"], list) or not set(rec["checks"]) <= set(props["checks"]["items"]["enum"]):
        problems.append("checks must list kinds of independent check only")
    if not re.fullmatch(props["quarter"]["pattern"].strip("^$"), str(rec["quarter"])):
        problems.append("quarter must look like 2026-Q4")
    try:
        dt.date.fromisoformat(str(rec["as_of"]))
    except ValueError:
        problems.append("as_of must be a date written YYYY-MM-DD")
    if not SHA.match(str(rec["log_sha256"])):
        problems.append("log_sha256 must be 64 hexadecimal characters")
    scorer = rec["scorer"]
    if not isinstance(scorer, dict) or scorer.get("name") != "horizon.py" or not SHA.match(str(scorer.get("sha256"))):
        problems.append("scorer must name horizon.py with its sha256")
    return problems


def short(digest):
    return f"{digest[:12]}..."


def normal(value):
    """Compare what a JSON reader sees, so 8 and 8.0 or tuples and lists do not count as differences."""
    return json.loads(json.dumps(value))


def check(rec, records, log_hash, scorer_hash):
    """Print the three answers for one record and return True when all three are yes."""
    as_of = dt.date.fromisoformat(rec["as_of"])
    title = f"{rec['person']} / {rec['domain']}"
    print(f"{title} . {rec['rung']} . {rec['gain_step']} . {rec['quarter']} (scored on {rec['as_of']})")
    same_log = rec["log_sha256"] == log_hash
    print("  log: the file that was scored (sha256 " + short(log_hash) + ")" if same_log else
          f"  log: not the file that was scored (the record names {short(rec['log_sha256'])}, this file is "
          f"{short(log_hash)})")
    same_scorer = rec["scorer"]["sha256"] == scorer_hash
    print("  scorer: the same horizon.py (sha256 " + short(scorer_hash) + ")" if same_scorer else
          f"  scorer: not the horizon.py that scored the record (the record names {short(rec['scorer']['sha256'])}, "
          f"here {short(scorer_hash)}); its rules may differ")
    found = [s for s in record_card.summarise(records, as_of)
             if s["person"] == rec["person"] and s["domain"] == rec["domain"]]
    if not found:
        longest = max(days for *_, days in horizon.RUNGS)
        print(f"  rescored on {rec['as_of']}: the log has no pieces of {rec['person']} in {rec['domain']} "
              f"in the {longest} days before that date")
        print(f"NO MATCH: {title}")
        return False
    expected = normal(record_card.export(found[0], log_hash, scorer_hash))
    given = normal(rec)
    differences = [f"    {key}: the record says {given[key]}, the log gives {expected[key]}"
                   for key in expected if key not in ("log_sha256", "scorer") and given.get(key) != expected[key]]
    if differences:
        print(f"  rescored on {rec['as_of']}: {len(differences)} field(s) differ")
        print("\n".join(differences))
    else:
        print(f"  rescored on {rec['as_of']}: the same record, field by field")
    ok = same_log and same_scorer and not differences
    print(f"MATCH: {title} . {rec['rung']} . {rec['gain_step']} . {rec['quarter']}" if ok else f"NO MATCH: {title}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record", help="the portable record: record_card.py --format json (one or more lines)")
    ap.add_argument("log", help="the log it says it comes from: .jsonl (Appendix C1) or .csv (templates/work-log.csv)")
    args = ap.parse_args(argv)
    try:
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        recs = read_records(args.record)
    except (OSError, ValueError) as err:
        print(f"the record could not be read: {err}")
        sys.exit(2)
    for n, rec in enumerate(recs, 1):
        problems = schema_problems(rec, schema)
        if problems:
            print(f"the record could not be read: record {n} does not follow export-record.schema.json: "
                  + "; ".join(problems))
            sys.exit(2)
    try:
        records = record_card.load_any(args.log)
        log_hash, scorer_hash = record_card.sha256(args.log), record_card.sha256(horizon.__file__)
    except SystemExit as stop:                     # horizon.load refuses a line that breaks the rules
        print(f"the log could not be read: {stop.code}")
        sys.exit(2)
    except (OSError, ValueError, KeyError, TypeError) as err:
        print(f"the log could not be read: {err}")
        sys.exit(2)
    matched = sum(check(rec, records, log_hash, scorer_hash) for rec in recs)
    print(f"{matched} of {len(recs)} records match")
    sys.exit(0 if matched == len(recs) else 1)


if __name__ == "__main__":
    main()
