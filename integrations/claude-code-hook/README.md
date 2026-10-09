# Agent-session hook: never lose a failed piece

The work log of Appendix C1 is only as good as its failures. People write down what worked and forget
what did not, which inflates the pass share (Table 4a, "hiding failures"). This hook moves the burden
from memory to the tool: every time an agent session ends, one pending entry is opened, and closing
it later takes a minute of questions.

## Install (Claude Code)

1. Copy the `hooks` block of `settings-example.json` into `~/.claude/settings.json` (all projects) or
   `.claude/settings.json` inside one project, and replace `/ABSOLUTE/PATH/TO` with the folder where
   you cloned this repository.
2. Optional: set `HORIZON_PENDING` to choose where pending entries go
   (default `~/.delegation-horizon/pending.jsonl`).

Any other agent CLI that can run a shell command when a session ends works the same way: point it at
`open-handover.sh`. If the tool passes no JSON on stdin, the entry still records the date and folder.

## Close the open entries (once a day or once a week)

```bash
python3 tools/log_piece.py my-log.jsonl --pending ~/.delegation-horizon/pending.jsonl
```

For each session it asks whether a piece of work was handed over; if yes, it asks the questions of
Appendix C1 (accepted, rejected or abandoned; which check; reference hours; your minutes) and appends
a line that `horizon.py` and `checker.html` read as they are. Failed and abandoned pieces are logged
too: they are part of the denominator.

## What it does not do

It reads no transcript, sends nothing over the network and records no content of the session: only
the date, the folder and the session id that the tool hands it.
