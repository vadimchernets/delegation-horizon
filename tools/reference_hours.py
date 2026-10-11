#!/usr/bin/env python3
"""reference_hours.py: turn the raters' estimates of a piece into its reference hours and the cells of its log line.

Teaches: the rater rule of Sections 5.1 and 5.8. Two raters, blind to the person, estimate the by-hand hours of a
qualified specialist. If the larger estimate is at most 1.5 times the smaller, the reference is their geometric
mean (the rule Appendix E3 tests); if they are further apart, a third rater is needed (Table 3), and with three
estimates the reference is their median, so the third estimate decides between the first two. A third estimate is
taken only when the first two disagree, so it cannot move a piece the first two placed. It prints the reference, the
rung size it reaches, and the cells reference_hours, reference_basis and rater_hours for the log; the reference is
rounded to one decimal and never rounded up across a rung threshold, so the log reaches the size printed.
Limits: the rule combines estimates; whether the raters were qualified and blind is for the audit
(kits/reference-hours-raters.md says how to choose and brief them).
Usage:
  python3 tools/reference_hours.py 6 10          two estimates in hours
  python3 tools/reference_hours.py 6 10 7        with the third rater's estimate
Licence: MIT
"""
import argparse
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (RATER_SPREAD and the rung sizes of Appendix C2)


def size_reached(hours):
    """The largest rung whose size the piece reaches."""
    return next((name for name, h, *_ in horizon.RUNGS if hours >= h), "below Hour")


def cell_value(reference):
    """reference rounded to one decimal, unless rounding would carry it over a rung threshold; then cut, not rounded."""
    value = round(reference, 1)
    if size_reached(value) != size_reached(reference):
        value = math.floor(reference * 10) / 10
    return value


def combine(estimates):
    """(reference hours, how it was reached, needs a third rater) for two or three positive estimates."""
    if len(estimates) == 2:
        a, b = estimates
        ratio = max(a, b) / min(a, b)
        if ratio <= horizon.RATER_SPREAD:
            return math.sqrt(a * b), f"geometric mean of two estimates {ratio:.2f} apart", False
        return None, f"the two estimates are {ratio:.2f} apart, more than {horizon.RATER_SPREAD}", True
    return statistics.median(estimates), "median of three estimates: the third decides between the first two", False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reference hours from the raters' estimates (Sections 5.1 and 5.8).")
    ap.add_argument("estimates", nargs="+", type=float, help="two estimates in hours, or three with the third rater's")
    args = ap.parse_args(argv)
    est = args.estimates
    if len(est) not in (2, 3) or min(est) <= 0 or not all(math.isfinite(x) for x in est):
        ap.error("give two positive estimates, or three when a third rater was needed")
    if len(est) == 3 and max(est[:2]) / min(est[:2]) <= horizon.RATER_SPREAD:
        ap.error(f"the first two estimates are {max(est[:2]) / min(est[:2]):.2f} apart, within {horizon.RATER_SPREAD}: "
                 "their geometric mean is the reference and a third estimate is not needed")
    reference, how, third = combine(est)
    cell = ";".join(f"{x:g}" for x in est)
    if third:
        print(f"needs a third rater: {how} (Table 3). Ask a third rater, blind to the person and to the first two, "
              f"then run again with three estimates.")
        print(f"rater_hours cell so far: {cell}")
        return
    value = cell_value(reference)
    print(f"reference hours {value:.1f} ({how}); the piece reaches {size_reached(value)} size")
    print(f"log cells: reference_hours {value:g}, reference_basis two raters"
          f"{' and a third' if len(est) == 3 else ''}, rater_hours {cell}")


if __name__ == "__main__":
    main()
