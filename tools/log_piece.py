#!/usr/bin/env python3
"""log_piece.py: write one line of the work log by answering questions, instead of typing JSON.

Teaches: what Appendix C1 asks about every piece handed to agents, including the failed and the
abandoned ones, and why each field is there. The line is checked with horizon.py's own rules before
it is written, so the log always stays readable by horizon.py and record_card.py.
Limits: it records what the person says. It cannot tell whether a check was really independent or
whether the reference hours are fair; that is what the audit checklist in kits/ is for.
Usage:
  python3 tools/log_piece.py my-log.jsonl                      ask the questions, append one line
  python3 tools/log_piece.py my-log.jsonl --pending pending.jsonl
        close the hand-overs that the agent hook (integrations/) opened, one by one
Answers can also be piped in, one per line, in the order of the questions (useful in scripts).
Licence: MIT
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (the scorer of Appendix C2; its rules validate the line)

# key, question, kind, default ("" means the answer is required)
QUESTIONS = [
    ("person", "Pseudonymous label for the person (never a real name)", "text", ""),
    ("domain", "Domain in which the work was accepted or rejected", "text", ""),
    ("started", "Date the hand-over started (YYYY-MM-DD, blank if same day)", "date?", ""),
    ("date", "Date it closed: accepted, rejected or abandoned (YYYY-MM-DD)", "date", "today"),
    ("reference_hours", "By-hand hours a qualified specialist would need for the whole deliverable", "number", ""),
    ("reference_basis", "Where that number comes from (a named task bank, or two raters)", "text", "two raters"),
    ("attention_minutes", "Your minutes of planning, instructing, reading, checking and fixing", "number", ""),
    ("mode", "Mode: one_piece, stages or together", "choice:" + ",".join(sorted(horizon.MODES)), "stages"),
    ("check", "Check used: " + ", ".join(sorted(horizon.CHECKS)), "choice:" + ",".join(sorted(horizon.CHECKS)), ""),
    ("agent_saw_check", "Could the agents see the check? (yes/no)", "bool", "no"),
    ("passed", "Did it pass the check? (no for failed or abandoned work)", "bool", ""),
    ("irreversible", "Would a mistake in this kind of work be impossible to undo? (yes/no)", "bool", "no"),
    ("planted_errors", "How many errors were planted in the task before hand-over", "int", "0"),
    ("planted_missed", "How many of them were not caught", "int", "0"),
    ("outside_help", "Did a colleague or contractor help off the log? (yes/no)", "bool", "no"),
]
YES, NO = {"yes", "y", "true", "1"}, {"no", "n", "false", "0"}


def convert(kind, raw):
    """Turn a typed answer into the value the log stores; raise ValueError with a plain message."""
    if kind == "text":
        if not raw:
            raise ValueError("an answer is required")
        return raw
    if kind in ("date", "date?"):
        if not raw and kind == "date?":
            return None
        return dt.date.fromisoformat(raw).isoformat()
    if kind == "number":
        value = float(raw)
        return int(value) if value.is_integer() else value
    if kind == "int":
        value = int(raw)
        if value < 0:
            raise ValueError("must not be negative")
        return value
    if kind == "bool":
        if raw.lower() in YES:
            return True
        if raw.lower() in NO:
            return False
        raise ValueError("answer yes or no")
    if kind.startswith("choice:"):
        allowed = kind.split(":", 1)[1].split(",")
        if raw not in allowed:
            raise ValueError("choose one of " + ", ".join(allowed))
        return raw
    raise ValueError("unknown kind " + kind)


def ask(preset=None, read=input, write=print):
    """Ask every question not already answered in preset; return a dict ready for the log."""
    record = dict(preset or {})
    for key, question, kind, default in QUESTIONS:
        if key in record:
            continue
        shown_default = dt.date.today().isoformat() if default == "today" else default
        while True:
            try:
                raw = read(f"{question}" + (f" [{shown_default}]" if shown_default else "") + ": ").strip()
            except EOFError:
                sys.exit(f"input ended before the question about {key}")
            raw = raw or shown_default
            try:
                value = convert(kind, raw)
                break
            except ValueError as exc:
                write(f"  not accepted: {exc}")
        if value is not None:
            record[key] = value
    return record


def check_with_horizon(record):
    """Run the line through horizon.load, so it obeys exactly the rules of the scorer."""
    fd, tmp = tempfile.mkstemp(suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        horizon.load(tmp)
    finally:
        os.remove(tmp)


def append(path, record):
    check_with_horizon(record)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Append one piece of work to a JSON Lines work log.")
    ap.add_argument("log", help="the work log to append to (created if missing)")
    ap.add_argument("--pending", help="a pending file written by the agent hook; close each open hand-over")
    args = ap.parse_args()
    if not args.pending:
        append(args.log, ask())
        print(f"one line added to {args.log}")
        return
    with open(args.pending, encoding="utf-8") as fh:
        stubs = [json.loads(line) for line in fh if line.strip()]
    for stub in stubs:
        print(f"\nOpen hand-over from {stub.get('started', '?')} in {stub.get('cwd', '?')}"
              f" (session {stub.get('session', '?')})")
        if input("Was a piece of work handed over in this session? (yes/no) [yes]: ").strip().lower() in NO:
            continue
        preset = {"started": stub["started"]} if stub.get("started") else {}
        append(args.log, ask(preset))
    open(args.pending, "w", encoding="utf-8").close()
    print(f"\n{len(stubs)} hand-over(s) closed and added to {args.log}")


if __name__ == "__main__":
    main()
