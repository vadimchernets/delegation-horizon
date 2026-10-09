#!/usr/bin/env bash
# open-handover.sh: an agent-CLI hook that opens a work-log entry every time an agent session ends.
#
# Teaches: the commonest hole in a work log is the piece that failed and was never written down
# (Table 4a, "hiding failures"). This hook makes the log ask instead of remember: at the end of each
# session it appends one pending line (date, folder, session id) to a pending file. Later,
# `python3 tools/log_piece.py my-log.jsonl --pending <pending file>` walks through the open entries and
# asks the questions of Appendix C1 (accepted or rejected, which check, how long), or lets you skip a
# session in which nothing was handed over.
# Limits: it records that a session happened, never what was in it; it reads no transcript and sends
# nothing anywhere. It works with any tool that can run a command at session end and pass JSON on
# stdin (the example settings are for Claude Code's SessionEnd hook).
# Usage: see README.md in this folder.     Licence: MIT
set -u
PENDING="${HORIZON_PENDING:-$HOME/.delegation-horizon/pending.jsonl}"
mkdir -p "$(dirname "$PENDING")"
python3 -c '
import datetime, json, os, sys
try:
    event = json.load(sys.stdin)
except ValueError:
    event = {}
line = {"started": datetime.date.today().isoformat(),
        "session": str(event.get("session_id", "")),
        "cwd": str(event.get("cwd", os.getcwd())),
        "reason": str(event.get("reason", ""))}
with open(sys.argv[1], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(line) + "\n")
' "$PENDING"
exit 0
