#!/usr/bin/env python3
"""prolific_to_long.py: turn Prolific Survey Builder exports into the input of human_raters.py.

Mechanical conversion only; every rule of the analysis lives in human_raters.py, registered
before data collection (OSF 10.17605/OSF.IO/V92R8).
- rater: a salted hash of the Prolific participant ID (the ID itself is not kept);
- task_id: from the question text "Task BK01: ..."; the repeated task "Task BK03 (again): ..."
  becomes "BK03-retest";
- reference_hours: the number given, divided by 60 when the participant chose minutes;
  anything that is not a number is kept as text and dropped by human_raters.py;
- attention_ok: 1 if the attention question was answered "Twelve";
- competency_ok: 1 if the competency question got its correct option.
Usage: python3 pilot/prolific_to_long.py out.csv bookkeeping=BK/responses.jsonl webtools=WT/responses.jsonl
Licence: MIT
"""
import csv
import hashlib
import json
import re
import sys

CORRECT = {
    "double-entry": "Debit bank, credit accounts receivable",
    "LEFT JOIN": "All rows of the left table, with matching rows of the right table or NULLs",
}
SALT = "delegation-horizon-prepilot-2026-10-09"


def number(text):
    m = re.search(r"\d+(?:[.,]\d+)?", str(text))
    return float(m.group(0).replace(",", ".")) if m else None


def convert(domain, path):
    rows = []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        rater = hashlib.sha256((SALT + r["participant_id"]).encode()).hexdigest()[:10]
        att = comp = "0"
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
            elif q["type"] == "free_text_with_unit":
                m = re.match(r"Task (\w\w\d\d)( \(again\))?:", d)
                if not m:
                    continue
                task = m.group(1) + ("-retest" if m.group(2) else "")
                n = number(q.get("value", ""))
                h = (n / 60 if q.get("unit") == "minutes" else n) if n is not None else q.get("value", "")
                estimates.append((task, h))
        for task, h in estimates:
            rows.append({"domain": domain, "rater": rater, "task_id": task, "reference_hours": h,
                         "attention_ok": att, "competency_ok": comp})
    return rows


def main():
    out = sys.argv[1]
    rows = []
    for arg in sys.argv[2:]:
        domain, path = arg.split("=", 1)
        rows += convert(domain, path)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["domain", "rater", "task_id", "reference_hours", "attention_ok", "competency_ok"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows, {len({(r['domain'], r['rater']) for r in rows})} participants -> {out}")


if __name__ == "__main__":
    main()
