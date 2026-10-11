#!/usr/bin/env python3
"""process_study.py: analyse the comparison of Section 10.5, experience in a trade crossed with the
way of working, with the two kinds of planted error scored apart.

Teaches: Section 10.5 crosses experience in the trade (present or absent, established by a screen
and a record of work, never by a profile label) with the way of working (one agent whose output is
accepted as it comes, or the checking process of Section 6.5), on the same tasks of the bank, under
checks the agents did not see. Omissions and wrong entries are scored apart: the list drawn up
before the work is aimed at the first, the reviewers at the second. For each kind of planted error,
and for verified pieces when given, this prints the four cells with Wilson 95% intervals; the process
effect among newcomers, the experience effect under one agent and their interaction (difference in
differences), each with a 95% interval from a bootstrap that resamples participants within each
cell; and the share of the experience gap the process closes, only where the interval of the
experience effect excludes zero. --power gives the size of such a study.
Limits: the cell intervals treat every planted error (or piece) as independent; the effect intervals
resample people, and they are the ones to read. A percentile bootstrap is too narrow with fewer than
about ten people in a cell. The first blocks pool the rungs, which is fair only when every cell got
tasks of the same sizes, as the protocol requires; --by-rung shows each rung. Nothing is corrected
for the number of contrasts: the registration names the primary ones in advance
(kits/process-vs-experience-study.md). --power is a normal approximation for two proportions.
Usage:
  python3 tools/process_study.py errors.csv [--pieces pieces.csv] [--by-rung] [--seed 20261010] [--reps 2000]
      errors.csv: one row per planted error, columns participant, experience (present or absent),
      way (one_agent or process), rung (Hour, Day, Week, Month or Quarter), kind (wrong_entry or
      omission), caught (1 or 0). pieces.csv: one row per piece, the same first four columns and
      verified (1 or 0).
  python3 tools/process_study.py --power 0.40 0.60 [--n 60] [--per-person 3 --icc 0.2]
Licence: MIT
"""
import argparse
import csv
import io
import math
import os
import random
import sys
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (the names of the rungs come from the scorer)

SEED = 20261010
REPS = 2000
ALPHA = 0.05
TARGET_POWER = 0.80
EXPERIENCE = ("absent", "present")
WAYS = ("one_agent", "process")
KINDS = ("wrong_entry", "omission")
CELLS = [(e, w) for e in EXPERIENCE for w in WAYS]
RUNG_NAMES = [r[0] for r in sorted(horizon.RUNGS, key=lambda r: r[1])]      # Hour, Day, Week, Month, Quarter
ERROR_COLUMNS = ("participant", "experience", "way", "rung", "kind", "caught")
PIECE_COLUMNS = ("participant", "experience", "way", "rung", "verified")
EFFECTS = ("process_newcomers", "experience_one_agent", "interaction")
LABELS = {
    "process_newcomers": "process effect among newcomers (absent: process - one_agent)",
    "experience_one_agent": "experience effect under one agent (one_agent: present - absent)",
    "interaction": "interaction, difference in differences (process effect among the experienced minus"
                   " among newcomers)",
}


def wilson(k, n, z=NormalDist().inv_cdf(1 - ALPHA / 2)):
    """Wilson score interval for k successes in n trials (Wilson, 1927)."""
    if n < 1 or not 0 <= k <= n:
        raise ValueError("need n >= 1 and 0 <= k <= n")
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def read_rows(path, columns, cell_of):
    """Rows as dicts (participant, cell, rung, kind, outcome); exits with one line on bad input.
    cell_of maps each participant to the cell where they were first seen, across both files."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError as exc:
        sys.exit(f"{path}: {exc.strerror or exc}")
    except UnicodeDecodeError:
        sys.exit(f"{path}: not a UTF-8 text file")
    first = text.split("\n", 1)[0]
    if not first.strip():
        sys.exit(f"{path}: empty file, expected a header with {', '.join(columns)}")
    reader = csv.DictReader(io.StringIO(text), delimiter=";" if ";" in first and "," not in first else ",")
    reader.fieldnames = [(name or "").strip() for name in reader.fieldnames]
    missing = [c for c in columns if c not in reader.fieldnames]
    if missing:
        sys.exit(f"{path}: missing column(s) {', '.join(missing)}; needed: {', '.join(columns)}")
    outcome = columns[-1]
    allowed = {"experience": EXPERIENCE, "way": WAYS, "kind": KINDS}
    rows = []
    try:
        for row_no, raw in enumerate(reader, 2):
            v = {c: (raw.get(c) or "").strip() for c in columns}
            if not v["participant"]:
                sys.exit(f"{path} row {row_no}: participant is empty")
            for c in allowed:
                if c in v:
                    v[c] = v[c].lower()
                    if v[c] not in allowed[c]:
                        sys.exit(f"{path} row {row_no}: {c} {v[c]!r} is not one of {', '.join(allowed[c])}")
            rung = next((r for r in RUNG_NAMES if r.lower() == v["rung"].lower()), None)
            if rung is None:
                sys.exit(f"{path} row {row_no}: rung {v['rung']!r} is not one of {', '.join(RUNG_NAMES)}")
            if v[outcome] not in ("1", "0"):
                sys.exit(f"{path} row {row_no}: {outcome} must be 1 or 0, not {v[outcome]!r}")
            cell = (v["experience"], v["way"])
            known = cell_of.setdefault(v["participant"], (cell, path, row_no))
            if known[0] != cell:
                sys.exit(f"{path} row {row_no}: participant {v['participant']} is {cell[0]} / {cell[1]} here but"
                         f" {known[0][0]} / {known[0][1]} in {known[1]} row {known[2]}; experience and way"
                         " are fixed for each person")
            rows.append({"participant": v["participant"], "cell": cell, "rung": rung,
                         "kind": v.get("kind", "piece"), "outcome": int(v[outcome])})
    except csv.Error as exc:
        sys.exit(f"{path}: {exc}")
    if not rows:
        sys.exit(f"{path}: no rows of data")
    return rows


def clusters(rows):
    """{cell: [(successes, total), ...]}, one pair per participant, in a fixed order."""
    acc = {}
    for r in rows:
        pair = acc.setdefault(r["cell"], {}).setdefault(r["participant"], [0, 0])
        pair[0] += r["outcome"]
        pair[1] += 1
    return {cell: [tuple(people[p]) for p in sorted(people)] for cell, people in acc.items()}


def shares(groups):
    out = {}
    for cell in CELLS:
        people = groups.get(cell)
        out[cell] = sum(s for s, _ in people) / sum(t for _, t in people) if people else None
    return out


def contrasts(sh):
    """The process effect among newcomers, the experience effect under one agent, and the interaction."""
    a1, ap = sh[("absent", "one_agent")], sh[("absent", "process")]
    p1, pp = sh[("present", "one_agent")], sh[("present", "process")]
    process = None if a1 is None or ap is None else ap - a1
    experience = None if a1 is None or p1 is None else p1 - a1
    interaction = None if None in (a1, ap, p1, pp) else (pp - p1) - (ap - a1)
    return process, experience, interaction


def resample(groups, rng):
    """One bootstrap replicate: in each cell, as many participants as it has, drawn with replacement."""
    out = {}
    for cell in CELLS:
        people = groups.get(cell)
        if not people:
            out[cell] = None
            continue
        n, s, t = len(people), 0, 0
        for _ in range(n):
            a, b = people[int(rng.random() * n)]
            s += a
            t += b
        out[cell] = s / t
    return out


def percentile(values, q):
    """Linear interpolation between order statistics, the default of most statistics packages."""
    v = sorted(values)
    pos = q * (len(v) - 1)
    i = int(pos)
    return v[i] if i + 1 >= len(v) else v[i] + (v[i + 1] - v[i]) * (pos - i)


def analyse(rows, reps=REPS, seed=SEED, stream="all"):
    """rows: dicts with participant, cell (experience, way) and outcome (1 or 0), all of one kind.
    Each analysis draws from its own random stream, named by the seed and the stream, so adding
    another kind, the pieces or --by-rung never changes the intervals of an analysis."""
    groups = clusters(rows)
    point = contrasts(shares(groups))
    rng = random.Random(f"{seed}/{stream}")
    draws = [contrasts(resample(groups, rng)) for _ in range(reps)]
    effects = {}
    for j, name in enumerate(EFFECTS):
        values = [d[j] for d in draws]
        effects[name] = None if point[j] is None else (point[j], percentile(values, ALPHA / 2),
                                                        percentile(values, 1 - ALPHA / 2))
    cells = {}
    for cell in CELLS:
        people = groups.get(cell, [])
        cells[cell] = (sum(s for s, _ in people), sum(t for _, t in people), len(people))
    ratios = [d[0] / d[1] for d in draws if d[0] is not None and d[1]]
    return {"cells": cells, "effects": effects, "ratios": ratios}


def points(x):
    return f"{round(x * 100, 1) + 0.0:+.1f}"


def gap_share(result):
    """((share, low, high), "") for the share of the experience gap the process closes, or
    (None, reason) when it is not printed: only an experience effect whose interval excludes zero
    is a gap to divide by."""
    process = result["effects"]["process_newcomers"]
    experience = result["effects"]["experience_one_agent"]
    if process is None or experience is None:
        return None, "not printed, because a cell it needs has no data"
    est, lo, hi = experience
    if lo <= 0 <= hi or est == 0:
        return None, (f"not printed, because the 95% interval of the experience effect under one agent"
                      f" ({points(lo)} to {points(hi)} points) includes zero, so there is no established gap"
                      " to divide by")
    if hi < 0:
        return None, ("not printed, because the experience effect under one agent is negative: newcomers did"
                      " better than experienced people, so there is no gap for the process to close")
    ratios = result["ratios"]
    return (process[0] / est, percentile(ratios, ALPHA / 2), percentile(ratios, 1 - ALPHA / 2)), ""


def render(title, result, what):
    """The lines of one block; what is 'caught' for planted errors and 'verified' for pieces."""
    lines = [f"== {title} ==",
             f"  {'cell':<22}{what + '/total':<16}{'people':<8}{'share':<8}Wilson 95% interval"]
    for cell in CELLS:
        s, t, n = result["cells"][cell]
        name = f"{cell[0]} / {cell[1]}"
        if t:
            lo, hi = wilson(s, t)
            lines.append(f"  {name:<22}{f'{s}/{t}':<16}{n:<8}{s / t:<8.1%}{lo:.1%} to {hi:.1%}")
        else:
            lines.append(f"  {name:<22}{'0/0':<16}{0:<8}{'n/a':<8}no data in this cell")
    for name in EFFECTS:
        e = result["effects"][name]
        if e is None:
            lines.append(f"  {LABELS[name]}: n/a, a cell it needs has no data")
        else:
            lines.append(f"  {LABELS[name]}: {points(e[0])} points, 95% interval {points(e[1])} to {points(e[2])}")
    gap, reason = gap_share(result)
    head = "  share of the experience gap the process closes"
    if gap is None:
        lines.append(f"{head}: {reason}")
    else:
        lines.append(f"{head}: {gap[0]:.0%}, 95% interval {gap[1]:.0%} to {gap[2]:.0%}"
                     " (process effect among newcomers / experience effect under one agent)")
    return lines


def power(p1, p2, n, alpha=ALPHA):
    """Approximate power of a two-sided test of two proportions with n observations in each group
    (normal approximation without continuity correction, as R's power.prop.test)."""
    z = NormalDist().inv_cdf(1 - alpha / 2)
    pbar = (p1 + p2) / 2
    null = math.sqrt(2 * pbar * (1 - pbar))
    alternative = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return NormalDist().cdf((abs(p1 - p2) * math.sqrt(n) - z * null) / alternative)


def n_for_power(p1, p2, target=TARGET_POWER, alpha=ALPHA):
    """Observations per group for the target power, before rounding up (the inverse of power())."""
    z = NormalDist().inv_cdf(1 - alpha / 2)
    pbar = (p1 + p2) / 2
    null = math.sqrt(2 * pbar * (1 - pbar))
    alternative = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return ((z * null + NormalDist().inv_cdf(target) * alternative) / abs(p1 - p2)) ** 2


def power_report(p1, p2, n, per_person, icc):
    need = n_for_power(p1, p2)
    lines = [f"two proportions {p1:g} and {p2:g}; two-sided test at {ALPHA:g}; normal approximation"
             " without continuity correction",
             "n counts observations per cell: planted errors of one kind, or pieces"]
    if n:
        lines.append(f"power with {n} per cell: {power(p1, p2, n):.2f}")
    lines.append(f"n per cell for {TARGET_POWER:.2f} power: {math.ceil(need)} ({4 * math.ceil(need)} in the four cells)")
    if per_person > 1 or icc > 0:
        deff = 1 + (per_person - 1) * icc
        people = math.ceil(need * deff / per_person)
        lines.append(f"design effect {deff:.2f} ({per_person} observations per person, correlation {icc:g}"
                     " within a person):")
        if n:
            lines.append(f"  power with {n} per cell: {power(p1, p2, n / deff):.2f}")
        lines.append(f"  n per cell for {TARGET_POWER:.2f} power: {people} people, {people * per_person}"
                     f" observations per cell ({4 * people} people in the four cells)")
    return lines


def main():
    ap = argparse.ArgumentParser(description="Analyse the comparison of Section 10.5: experience in a trade "
                                             "crossed with the way of working, planted errors scored apart by kind.")
    ap.add_argument("errors", nargs="?", help="CSV, one row per planted error: participant, experience, way, "
                                              "rung, kind, caught")
    ap.add_argument("--pieces", help="CSV, one row per piece: participant, experience, way, rung, verified")
    ap.add_argument("--by-rung", action="store_true", help="repeat every block for each rung")
    ap.add_argument("--seed", type=int, default=SEED, help=f"seed of the bootstrap, printed with the results "
                                                            f"(default {SEED})")
    ap.add_argument("--reps", type=int, default=REPS, help=f"bootstrap replicates (default {REPS})")
    ap.add_argument("--power", nargs=2, type=float, metavar=("P1", "P2"),
                    help="size a study instead: two proportions to tell apart")
    ap.add_argument("--n", type=int, help="with --power: observations per cell")
    ap.add_argument("--per-person", type=int, default=1, help="with --power: observations each person gives")
    ap.add_argument("--icc", type=float, default=0.0, help="with --power: correlation between two "
                                                           "observations of one person")
    args = ap.parse_args()
    if args.power:
        if args.errors or args.pieces:
            sys.exit("give either --power or the CSV files, not both")
        p1, p2 = args.power
        if not (0 < p1 < 1 and 0 < p2 < 1):
            sys.exit("--power: both proportions must lie between 0 and 1")
        if p1 == p2:
            sys.exit("--power: the two proportions are equal, and no study tells apart a difference of zero")
        if args.n is not None and args.n < 1:
            sys.exit("--n must be at least 1")
        if args.per_person < 1:
            sys.exit("--per-person must be at least 1")
        if not 0 <= args.icc <= 1:
            sys.exit("--icc must lie between 0 and 1")
        print("\n".join(power_report(p1, p2, args.n, args.per_person, args.icc)))
        return
    if not args.errors:
        sys.exit("give a CSV of planted errors (see --help), or --power P1 P2 to size a study")
    if args.n is not None or args.per_person != 1 or args.icc != 0:
        sys.exit("--n, --per-person and --icc go with --power")
    if args.reps < 100:
        sys.exit("--reps must be at least 100")
    cell_of = {}
    errors = read_rows(args.errors, ERROR_COLUMNS, cell_of)
    pieces = read_rows(args.pieces, PIECE_COLUMNS, cell_of) if args.pieces else []
    print("process_study.py: the comparison of Section 10.5, experience in the trade x way of working")
    by_kind = ", ".join(f"{sum(r['kind'] == k for r in errors)} {k}" for k in KINDS)
    print(f"planted errors: {args.errors} ({by_kind}; {len({r['participant'] for r in errors})} people)")
    if pieces:
        print(f"pieces: {args.pieces} ({len(pieces)} pieces; {len({r['participant'] for r in pieces})} people)")
    print(f"bootstrap: {args.reps} replicates, participants resampled within each cell, seed {args.seed}")
    print("cell intervals: Wilson, each row counted as independent; effect intervals: the bootstrap")
    rungs = [None]
    if args.by_rung:
        rungs += [name for name in RUNG_NAMES if any(r["rung"] == name for r in errors + pieces)]
    for rung in rungs:
        where = "all rungs" if rung is None else f"rung {rung}"
        for kind in KINDS:
            subset = [r for r in errors if r["kind"] == kind and (rung is None or r["rung"] == rung)]
            title = f"planted errors of kind {kind}, {where}"
            print()
            if not subset:
                print(f"== {title} ==\n  no planted errors of this kind" + ("" if rung is None else " at this rung"))
                continue
            print("\n".join(render(title, analyse(subset, args.reps, args.seed, f"{kind}/{rung or 'all'}"), "caught")))
        if pieces:
            subset = [r for r in pieces if rung is None or r["rung"] == rung]
            print()
            if not subset:
                print(f"== verified pieces, {where} ==\n  no pieces at this rung")
                continue
            print("\n".join(render(f"verified pieces, {where}",
                                   analyse(subset, args.reps, args.seed, f"pieces/{rung or 'all'}"), "verified")))


if __name__ == "__main__":
    main()
