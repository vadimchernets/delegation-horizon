#!/usr/bin/env python3
"""gate_leak.py: how much a gate that admits people by a label leaks, read from a check of the trade.

Teaches: Section 6.2 sets two kinds of gate side by side. A label (a profile on a platform, a job
title, a degree and, in part, a licence) admits a person on what they say or once showed; a check of
the work admits them on what they do. Put a first-week question of the trade behind the label and
count who fails it: in the pre-pilot of Appendix G2, 11 of the 60 people that Prolific's filters
admitted to the bookkeeping sample answered such a question wrongly. This prints, per group, the
share failing with an exact (Clopper-Pearson) 95% interval, and the admission factor 1 / (1 - share):
how many people the label must admit for every one who passes the check, with the factor at both
ends of the interval.
Limits: one question is a narrow check (kits/trade-screen.md). A wrong answer can be haste or a
misread question, and a right one a guess or a chat model's answer; a question is itself a weaker
gate than a check of delivered work. The interval treats the people admitted as independent draws
from one population, and says nothing about the people the label turned away.
Usage:
  python3 tools/gate_leak.py --admitted 60 --failed 11 [--label "Prolific occupation filter"]
  python3 tools/gate_leak.py answers.csv
      one row per person, columns participant, group, admitted_by, answer_correct (1 or 0)
Licence: MIT
"""
import argparse
import csv
import io
import math
import sys

LEVEL = 0.95
COLUMNS = ("participant", "group", "admitted_by", "answer_correct")


def _log_choose(n):
    """log C(n, j) for j = 0..n, so the tails below never build huge integers."""
    lg = math.lgamma
    return [lg(n + 1) - lg(j + 1) - lg(n - j + 1) for j in range(n + 1)]


def _tail(log_choose, n, p, js):
    """Sum of the binomial probabilities P(X = j) over js, for 0 < p < 1."""
    lp, lq = math.log(p), math.log1p(-p)
    return sum(math.exp(log_choose[j] + j * lp + (n - j) * lq) for j in js)


def _bisect(f, target, increasing):
    """The p in (0, 1) where the monotone function f crosses target, to the precision of a float."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        if (f(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k, n, level=LEVEL):
    """Exact two-sided interval for a binomial share k / n (Clopper and Pearson, 1934).
    The lower end is the p at which P(X >= k) equals (1 - level) / 2, the upper end the p at which
    P(X <= k) does; each is found by bisection on the exact binomial tail."""
    if not (isinstance(k, int) and isinstance(n, int)) or n < 1 or not 0 <= k <= n:
        raise ValueError("need whole numbers with n >= 1 and 0 <= k <= n")
    if not 0 < level < 1:
        raise ValueError("level must lie between 0 and 1")
    alpha = (1 - level) / 2
    log_choose = _log_choose(n)
    lo = 0.0 if k == 0 else _bisect(lambda p: _tail(log_choose, n, p, range(k, n + 1)), alpha, True)
    hi = 1.0 if k == n else _bisect(lambda p: _tail(log_choose, n, p, range(0, k + 1)), alpha, False)
    return lo, hi


def admission_factor(share):
    """How many people the label must admit for every one who passes the check: 1 / (1 - share)."""
    return math.inf if share >= 1 else 1 / (1 - share)


def leak(failed, admitted):
    lo, hi = clopper_pearson(failed, admitted)
    share = failed / admitted
    return {"admitted": admitted, "failed": failed, "share": share, "low": lo, "high": hi,
            "factor": admission_factor(share), "factor_low": admission_factor(lo),
            "factor_high": admission_factor(hi)}


def factor_text(x):
    return "unbounded" if math.isinf(x) else f"{x:.2f}"


def describe(title, r, labels=1):
    """The lines printed for one gate."""
    lines = [title,
             f"  admitted by the label{'s' if labels > 1 else ''}: {r['admitted']}",
             f"  failed the check of the trade: {r['failed']}",
             f"  share failing: {r['share']:.1%} (exact 95% interval {r['low']:.1%} to {r['high']:.1%},"
             " Clopper-Pearson)"]
    if math.isinf(r["factor"]):
        lines.append("  admission factor: unbounded, since nobody the label admitted passed the check")
    else:
        lines.append(f"  admission factor: {r['factor']:.2f} ({factor_text(r['factor_low'])} to"
                     f" {factor_text(r['factor_high'])}): the label must admit {r['factor']:.2f} people"
                     " for every one who passes the check")
    return lines


def read_answers(path):
    """{group: {label: [admitted, failed]}} from a CSV with one row per person; exits on bad input."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError as exc:
        sys.exit(f"{path}: {exc.strerror or exc}")
    except UnicodeDecodeError:
        sys.exit(f"{path}: not a UTF-8 text file")
    first = text.split("\n", 1)[0]
    if not first.strip():
        sys.exit(f"{path}: empty file, expected a header with {', '.join(COLUMNS)}")
    delimiter = ";" if ";" in first and "," not in first else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    reader.fieldnames = [(name or "").strip() for name in reader.fieldnames]
    missing = [c for c in COLUMNS if c not in reader.fieldnames]
    if missing:
        sys.exit(f"{path}: missing column(s) {', '.join(missing)}; needed: {', '.join(COLUMNS)}")
    gates, seen = {}, {}
    try:
        for row_no, row in enumerate(reader, 2):
            value = {c: (row.get(c) or "").strip() for c in COLUMNS}
            for c in ("participant", "group", "admitted_by"):
                if not value[c]:
                    sys.exit(f"{path} row {row_no}: {c} is empty")
            if value["answer_correct"] not in ("1", "0"):
                sys.exit(f"{path} row {row_no}: answer_correct must be 1 or 0, not {value['answer_correct']!r}")
            if value["participant"] in seen:
                sys.exit(f"{path} row {row_no}: participant {value['participant']} already has row"
                         f" {seen[value['participant']]} (one row per person)")
            seen[value["participant"]] = row_no
            count = gates.setdefault(value["group"], {}).setdefault(value["admitted_by"], [0, 0])
            count[0] += 1
            count[1] += value["answer_correct"] == "0"
    except csv.Error as exc:
        sys.exit(f"{path}: {exc}")
    if not gates:
        sys.exit(f"{path}: no rows of data")
    return gates


def main():
    ap = argparse.ArgumentParser(description="How much a gate that admits by a label leaks: the share of the "
                                             "people it admitted who fail a check of the trade.")
    ap.add_argument("answers", nargs="?", help="CSV, one row per person: participant, group, admitted_by, "
                                               "answer_correct (1 or 0)")
    ap.add_argument("--admitted", type=int, help="how many people the label admitted")
    ap.add_argument("--failed", type=int, help="how many of them failed the check of the trade")
    ap.add_argument("--label", help="name of the label, for example 'Prolific occupation filter'")
    args = ap.parse_args()
    counts = args.admitted is not None or args.failed is not None
    if args.answers and counts:
        sys.exit("give either a CSV of answers or --admitted and --failed, not both")
    if args.answers and args.label:
        sys.exit("--label goes with --admitted and --failed; in a CSV the column admitted_by names the label")
    if not args.answers and not counts:
        sys.exit("give a CSV of answers, or --admitted and --failed (see --help)")
    if counts:
        if args.admitted is None or args.failed is None:
            sys.exit("give both --admitted and --failed")
        if args.admitted < 1:
            sys.exit("--admitted must be at least 1")
        if not 0 <= args.failed <= args.admitted:
            sys.exit("--failed must lie between 0 and --admitted")
        print("\n".join(describe(f"gate: {args.label or 'label not named'}", leak(args.failed, args.admitted))))
        return
    blocks = []
    for group, labels in sorted(read_answers(args.answers).items()):
        admitted = sum(a for a, _ in labels.values())
        failed = sum(f for _, f in labels.values())
        if len(labels) == 1:
            title = f"{group}: admitted by {next(iter(labels))}"
        else:
            title = f"{group}: admitted by {len(labels)} labels"
        lines = describe(title, leak(failed, admitted), len(labels))
        if len(labels) > 1:
            lines.append("  by label:")
            for label, (a, f) in sorted(labels.items()):
                r = leak(f, a)
                lines.append(f"    {label}: {f} of {a} failed, {r['share']:.1%} ({r['low']:.1%} to {r['high']:.1%}),"
                             f" factor {factor_text(r['factor'])} ({factor_text(r['factor_low'])} to"
                             f" {factor_text(r['factor_high'])})")
        blocks.append("\n".join(lines))
    print("\n\n".join(blocks))


if __name__ == "__main__":
    main()
