#!/usr/bin/env python3
"""audit_sample.py: draw the accepted pieces that go to a second, independent check.

Teaches: the audit defence of Table 3. A record is only as good as its checks, and the cheapest way
to keep checks independent is to re-check a random share of accepted pieces with a second checker who
does not know which pieces were drawn in advance. The draw is reproducible: the same log, seed and
date always give the same pieces, so anyone can confirm that the sample was not hand-picked.
Nobody can steer it: a seed known while the log is written (such as the date) would let the person
logging compute which lines get drawn and arrange the log around them. So the default seed is taken
from the SHA-256 of the closed log file, the date and a salt the second checker chooses after
receiving the log (commit, then reveal): the log is fixed before the salt exists, and the salt is
chosen without seeing the draw. The log's SHA-256 and the seed are printed with the sample.
Every person and domain with an accepted piece gets at least one piece checked, and every accepted
irreversible piece can be forced into the sample with --all-irreversible.
Limits: it draws the sample and nothing else. It does not run the second check, and a share that is
too small will miss rare problems; 10 percent with a minimum of one per person and domain is a start.
Usage:
  python3 audit_sample.py team-log.csv --as-of 2026-10-09 --salt <word the second checker picks>
  python3 audit_sample.py team-log.csv --as-of 2026-10-09 --seed 20261009   # replay a printed seed
  python3 audit_sample.py team-log.jsonl --share 0.2 --format csv --out audit.csv
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import hashlib
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import horizon  # noqa: E402  (the scorer of Appendix C2, unchanged)
import record_card  # noqa: E402  (reads JSON Lines or the spreadsheet template)

FIELDS = ["line", "person", "domain", "date", "reference_hours", "check", "irreversible",
          "planted_errors", "reason"]


def accepted(r):
    """A piece the person signed off as passed; only these can be audited."""
    return r["passed"] is True


def derived_seed(log_bytes, as_of, salt=""):
    """The seed nobody can know while the log is written: SHA-256 of the closed log, the date and the salt."""
    log_sha = hashlib.sha256(log_bytes).hexdigest()
    mixed = hashlib.sha256(f"{log_sha}:{as_of.isoformat()}:{salt}".encode("utf-8")).hexdigest()
    return int(mixed[:16], 16), log_sha


def draw(records, as_of, share=0.1, seed=None, days=horizon.GAIN_WINDOW, all_irreversible=False):
    """Return the drawn pieces, each with its line number in the log and the reason it was drawn."""
    if not 0 < share <= 1:
        raise ValueError("share must lie in (0, 1]")
    seed = int(as_of.strftime("%Y%m%d")) if seed is None else seed
    rng = random.Random(seed)
    start = as_of - dt.timedelta(days=days)
    groups = defaultdict(list)
    for n, r in enumerate(records, 1):
        if start < r["date"] <= as_of and accepted(r):
            groups[(r["person"], r["domain"])].append((n, r))
    out = []
    for key in sorted(groups):
        pieces = groups[key]
        forced = [p for p in pieces if all_irreversible and p[1]["irreversible"]]
        rest = [p for p in pieces if p not in forced]
        k = max(1, math.ceil(share * len(pieces))) - len(forced)
        picked = rng.sample(rest, min(max(k, 0), len(rest)))
        out += [(n, r, "irreversible") for n, r in forced]
        out += [(n, r, "random") for n, r in picked]
    return sorted(out, key=lambda p: p[0]), seed


def rows(sample):
    for n, r, reason in sample:
        yield {"line": n, "person": r["person"], "domain": r["domain"], "date": r["date"].isoformat(),
               "reference_hours": r["reference_hours"], "check": r["check"],
               "irreversible": "yes" if r["irreversible"] else "no",
               "planted_errors": r["planted_errors"], "reason": reason}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log", help="work log: .jsonl (Appendix C1) or .csv (templates/work-log.csv)")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--share", type=float, default=0.1, help="share of accepted pieces to re-check (0.1)")
    ap.add_argument("--seed", type=int, help="replay a printed seed; by default the seed comes from the SHA-256 of the "
                    "log, the date and --salt")
    ap.add_argument("--salt", default="", help="a word the second checker picks after receiving the log")
    ap.add_argument("--days", type=int, default=horizon.GAIN_WINDOW, help="window in days (91)")
    ap.add_argument("--all-irreversible", action="store_true", help="always re-check irreversible pieces")
    ap.add_argument("--format", choices=["txt", "csv"], default="txt")
    ap.add_argument("--out", help="write here instead of the screen")
    args = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(args.as_of)
    records = record_card.load_any(args.log)
    with open(args.log, "rb") as fh:
        derived, log_sha = derived_seed(fh.read(), as_of, args.salt)
    seed_in = derived if args.seed is None else args.seed
    sample, seed = draw(records, as_of, args.share, seed_in, args.days, args.all_irreversible)
    fh = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    try:
        if args.format == "csv":
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows(sample))
        else:
            fh.write(f"audit sample as of {as_of}, seed {seed}, share {args.share:g}, window {args.days} days:"
                     f" {len(sample)} pieces\n")
            fh.write(f"log sha256 {log_sha}" + (f", salt {args.salt!r}" if args.salt else ", no salt") +
                     ("" if args.seed is None else "; seed given by hand") + "\n")
            for r in rows(sample):
                fh.write(f"  line {r['line']}: {r['person']} | {r['domain']} | {r['date']} |"
                         f" {r['reference_hours']} h | {r['check']} | {r['reason']}\n")
            fh.write("Give these pieces to a second checker who did not see the first check, and keep\n"
                     "the result of every re-check next to the original line, failures included.\n")
    finally:
        if args.out:
            fh.close()


if __name__ == "__main__":
    main()
