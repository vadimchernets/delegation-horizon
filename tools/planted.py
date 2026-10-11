#!/usr/bin/env python3
"""planted.py: seal a list of planted errors before the hand-over, score it by kind after, and summarise a study.

Teaches: a planted error is either a wrong entry or an omission of something the work must contain (Appendix A), and
the two are caught by different means: reviewers find what is wrong in a text, and only a list drawn up before the
work names what is missing from it (Section 6.5). The log keeps two counts (planted_errors, planted_missed), so the
kind lives in the sealed list beside it and horizon.py stays unchanged.
  seal     prints the SHA-256 of the list, to write into the task record before the hand-over, and its kinds;
  score    after acceptance: refuses a list that no longer matches its seal, and prints the two log fields and
           what was missed, by kind;
  summary  a ledger of the comparison of Section 10.5 (experience by way of working, one row per planted error):
           catch rates by kind in each cell and the contrasts that answer Section 6.5, with intervals from a
           bootstrap over people (errors of one person are not independent).
List CSV: error_id,kind,where,what,caught_if (kind: wrong_entry or omission). Outcome CSV: error_id,caught (yes/no).
Ledger CSV: person,experience,way,task_id,error_id,kind,caught (experience yes/no; way one_agent or process).
Usage:
  python3 tools/planted.py seal planted.csv
  python3 tools/planted.py score planted.csv outcome.csv --seal <sha256>
  python3 tools/planted.py summary ledger.csv [--draws 2000] [--seed 20261009]
Limits: it checks the bookkeeping of planted errors, not whether an error was well planted
(kits/planted-errors-guide.md says what makes a good one).
Licence: MIT
"""
import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict

KINDS = ("wrong_entry", "omission")
YES, NO = {"yes", "y", "true", "1"}, {"no", "n", "false", "0"}
CELLS = [("no", "one_agent"), ("no", "process"), ("yes", "one_agent"), ("yes", "process")]
CONTRASTS = [
    ("newcomer with the process minus expert who accepts on sight", ("no", "process"), ("yes", "one_agent")),
    ("the process without experience", ("no", "process"), ("no", "one_agent")),
    ("the process with experience", ("yes", "process"), ("yes", "one_agent")),
]


def read(path, needed=()):
    """Rows with every cell stripped (a missing cell is ""), after checking the header names the needed columns."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            head = [h.strip() for h in (reader.fieldnames or [])]
            missing = [c for c in needed if c not in head]
            if missing:
                sys.exit(f"{path}: the header lacks the column(s) {', '.join(missing)}")
            return [{(k or "").strip(): (v or "").strip() if isinstance(v, str) else "" for k, v in r.items()}
                    for r in reader]
    except OSError as err:
        sys.exit(f"{path}: {err.strerror}")


def flag(value, where):
    word = str(value).strip().lower()
    if word in YES:
        return True
    if word in NO:
        return False
    sys.exit(f"{where}: caught must be yes or no, got {value!r}")


def planted_list(path):
    rows, seen = read(path, ("error_id", "kind")), set()
    for n, r in enumerate(rows, 2):
        if r.get("kind", "") not in KINDS:
            sys.exit(f"row {n}: kind must be wrong_entry or omission, got {r.get('kind')!r}")
        if not r.get("error_id", "") or r["error_id"] in seen:
            sys.exit(f"row {n}: every error needs its own error_id")
        seen.add(r["error_id"])
    return rows


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def seal(args):
    rows = planted_list(args.list)
    kinds = Counter(r["kind"] for r in rows)
    print(f"sha256 {sha256(args.list)}  {args.list}")
    print(f"{len(rows)} planted: " + ", ".join(f"{kinds[k]} {k}" for k in KINDS))
    print("Write the hash into the task record before the hand-over; give the list to the auditor, not the person.")


def score(args):
    rows = planted_list(args.list)
    if args.seal and sha256(args.list) != args.seal.strip().lower():
        sys.exit(f"{args.list} does not match the seal: the list was changed after it was sealed")
    caught = {}
    for n, r in enumerate(read(args.outcome, ("error_id", "caught")), 2):
        if r["error_id"] in caught:
            sys.exit(f"outcome row {n}: {r['error_id']} is recorded twice; one row per planted error")
        caught[r["error_id"]] = flag(r["caught"], f"outcome {r['error_id']}")
    missing = [r["error_id"] for r in rows if r["error_id"] not in caught]
    if missing:
        sys.exit("no outcome for " + ", ".join(missing) + ": every planted error is recorded as caught or missed")
    missed = [r for r in rows if not caught[r["error_id"]]]
    print(("seal matches" if args.seal else "no seal given") + f": {args.list}")
    print(json.dumps({"planted_errors": len(rows), "planted_missed": len(missed)})[1:-1] + "   (fields of the log line)")
    for k in KINDS:
        print(f"  {k}: {sum(r['kind'] == k for r in rows)} planted, {sum(r['kind'] == k for r in missed)} missed")
    for r in missed:
        print(f"  missed {r['error_id']} ({r['kind']}): {r.get('what', '').strip()}")
    if missed:
        print("A missed planted error makes the piece unverified and blocks Week and above in the window (Section 5.2).")


def rates(by_person, people):
    """Caught share by kind over the given people (each person's errors pooled)."""
    out = {}
    for k in KINDS:
        hit = sum(by_person[p][k][0] for p in people)
        tot = sum(by_person[p][k][1] for p in people)
        out[k] = hit / tot if tot else float("nan")
    return out


def summary(args):
    by_person = defaultdict(lambda: {k: [0, 0] for k in KINDS})
    cell_of = {}
    for n, r in enumerate(read(args.ledger, ("person", "experience", "way", "error_id", "kind", "caught")), 2):
        cell = (r.get("experience", "").lower(), r.get("way", ""))
        if cell not in CELLS:
            sys.exit(f"row {n}: experience must be yes or no and way one_agent or process, got {cell}")
        if r.get("kind", "") not in KINDS:
            sys.exit(f"row {n}: kind must be wrong_entry or omission, got {r.get('kind')!r}")
        person = r["person"]
        if not person:
            sys.exit(f"row {n}: every row needs the person's label")
        if cell_of.setdefault(person, cell) != cell:
            sys.exit(f"row {n}: {person} appears in two cells")
        tally = by_person[person][r["kind"]]
        tally[0] += flag(r.get("caught", ""), f"row {n}")
        tally[1] += 1
    people = {c: sorted(p for p, pc in cell_of.items() if pc == c) for c in CELLS}
    point = {c: rates(by_person, people[c]) for c in CELLS}
    rng = random.Random(args.seed)
    draws = defaultdict(list)
    for _ in range(args.draws):
        boot = {c: rates(by_person, [rng.choice(people[c]) for _ in people[c]]) if people[c] else point[c] for c in CELLS}
        for c in CELLS:
            for k in KINDS:
                draws[(c, k)].append(boot[c][k])
        for name, a, b in CONTRASTS:
            for k in KINDS:
                draws[(name, k)].append(boot[a][k] - boot[b][k])

    def interval(key):
        xs = sorted(x for x in draws[key] if x == x)
        return (xs[int(0.025 * (len(xs) - 1))], xs[int(0.975 * (len(xs) - 1))]) if xs else (float("nan"),) * 2

    print(f"Planted errors caught, by kind (95% intervals from {args.draws} bootstrap draws over people, seed {args.seed})")
    print("experience  way        people  " + "  ".join(f"{k:24}" for k in KINDS))
    for c in CELLS:
        cells = []
        for k in KINDS:
            lo, hi = interval((c, k))
            tot = sum(by_person[p][k][1] for p in people[c])
            cells.append(f"{point[c][k]:.2f} ({lo:.2f} to {hi:.2f}) n={tot}".ljust(24))
        print(f"{c[0]:10}  {c[1]:9}  {len(people[c]):6}  " + "  ".join(cells))
    for name, a, b in CONTRASTS:
        for k in KINDS:
            lo, hi = interval((name, k))
            print(f"{name}: {k} {point[a][k] - point[b][k]:+.2f} (95% {lo:+.2f} to {hi:+.2f})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seal, score and summarise planted errors by kind.")
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("seal", help="hash a planted-error list before the hand-over")
    s.add_argument("list")
    s.set_defaults(func=seal)
    s = sub.add_parser("score", help="after acceptance: the log fields and what was missed, by kind")
    s.add_argument("list")
    s.add_argument("outcome")
    s.add_argument("--seal", help="the SHA-256 written into the task record before the hand-over")
    s.set_defaults(func=score)
    s = sub.add_parser("summary", help="catch rates by kind for the comparison of Section 10.5")
    s.add_argument("ledger")
    s.add_argument("--draws", type=int, default=2000)
    s.add_argument("--seed", type=int, default=20261009)
    s.set_defaults(func=summary)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
