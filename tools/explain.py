#!/usr/bin/env python3
"""explain.py: why a log earns the rung it earns, how much slack the rung has, and what the next rung needs.

Teaches: the rule of Section 5.2 one condition at a time. horizon.py prints the verdict, "Day (8/10)"; this prints
the reasons behind it from the same functions and constants (horizon.py unchanged): which condition holds or fails
and which piece decides, how many more failures the rung can absorb, the day it stops holding if nothing new is
logged, and every condition the next rung still lacks. For a count it also prints the exact 95% interval of the pass
rate that the count is consistent with (Section 5.8: eight of ten fit any rate from about 44% to 97%).
Limits: it explains the rule on the fields it is given, exactly as horizon.py scores them; whether a check was well
chosen or reference hours are fair is for the audit (kits/audit-checklist.md).
Usage:
  python3 tools/explain.py work-log.jsonl [--as-of 2026-10-09] [--person P07]
  python3 tools/explain.py my-log.csv                     (the spreadsheet template works too)
Licence: MIT
"""
import argparse
import datetime as dt
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (the scorer of Appendix C2, byte for byte)
import record_card  # noqa: E402  (reads a JSON Lines or a spreadsheet log through horizon.load)

LOOK_AHEAD = 366            # days scanned forward for "holds through" and "would hold from"


def passes_needed(n):
    """The fewest verified pieces out of n that meet the pass share, by the comparison horizon.py makes."""
    return next((k for k in range(n + 1) if n and k / n >= horizon.PASS_SHARE), 0)


def unmet(pieces, hours, minimum, as_of, days):
    """Every condition of horizon.rung_holds that fails, in plain words; an empty list exactly when the rung holds."""
    start = as_of - dt.timedelta(days=days)
    window = [r for r in pieces if start < r["date"] <= as_of]
    big = [r for r in window if float(r["reference_hours"]) >= hours]
    out = []
    if len(big) < minimum:
        note = f" ({sum(map(horizon.verified, big))} verified)" if big else ""
        out.append(f"{len(big)} pieces of at least {hours:g} h in the last {days} days{note}; {minimum} needed")
    if len(big) >= minimum and sum(map(horizon.verified, big)) / len(big) < horizon.PASS_SHARE:
        out.append(f"{sum(map(horizon.verified, big))} of {len(big)} verified; {passes_needed(len(big))} needed "
                   f"({horizon.PASS_SHARE:.0%} of the pieces)")
    for r in big:
        if r["irreversible"] and not horizon.verified(r):
            out.append(f"the irreversible piece closed {r['date']} is not verified (every irreversible piece must pass)")
    if hours >= horizon.PLANTED_FROM:
        if not any(int(r["planted_errors"]) > 0 for r in big):
            out.append("no piece of this size in the window carries planted errors")
        for r in window:
            if int(r["planted_missed"]) > 0:
                until = r["date"] + dt.timedelta(days=days)
                out.append(f"a planted error missed in the piece closed {r['date']} blocks Week and above until {until}"
                           f" (for this rung's {days}-day window)")
    if days > horizon.GAIN_WINDOW:
        recent = as_of - dt.timedelta(days=horizon.GAIN_WINDOW)
        if not any(horizon.verified(r) and r["date"] > recent for r in big):
            out.append(f"no verified piece of this size in the last {horizon.GAIN_WINDOW} days")
    return out


def binom_tail(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p), in logarithms so that a log of thousands of pieces does not overflow."""
    if p <= 0.0:
        return 1.0 if k <= 0 else 0.0
    if p >= 1.0:
        return 1.0
    lp, lq, top = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    return sum(math.exp(top - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * lp + (n - j) * lq)
               for j in range(max(k, 0), n + 1))


def solve(f, target):
    """The p in [0, 1] where the increasing function f reaches target, by bisection."""
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < target else (lo, mid)
    return (lo + hi) / 2


def exact_interval(k, n, level=0.95):
    """Clopper-Pearson interval for a pass rate after k passes in n pieces."""
    a = (1 - level) / 2
    low = 0.0 if k == 0 else solve(lambda p: binom_tail(k, n, p), a)
    high = 1.0 if k == n else solve(lambda p: binom_tail(k + 1, n, p), 1 - a)
    return low, high


def one_sided_lower(k, n, level=0.95):
    """One-sided lower bound of the pass rate; for k == n it is (1 - level) ** (1 / n), as Section 5.8 uses."""
    return 0.0 if k == 0 else solve(lambda p: binom_tail(k, n, p), 1 - level)


def rung_row(name):
    return next(r for r in horizon.RUNGS if r[0] == name)


def holds_through(pieces, name, as_of):
    """The last day the rung still holds if nothing new is logged, and the conditions that fail the day after: the
    reasons come from unmet(), the same reading of the rule, so a lapse under the 91-day rule is named as such."""
    _, hours, minimum, days = rung_row(name)
    for ahead in range(1, LOOK_AHEAD + 1):
        d = as_of + dt.timedelta(days=ahead)
        if not horizon.rung_holds(pieces, hours, minimum, d, days):
            return d - dt.timedelta(days=1), unmet(pieces, hours, minimum, d, days)
    return None, []


def leaving(pieces, name, day):
    """The dates of pieces of the rung's size that leave its window on day."""
    _, hours, _, days = rung_row(name)
    return sorted({str(r["date"]) for r in pieces
                   if r["date"] == day - dt.timedelta(days=days) and float(r["reference_hours"]) >= hours})


def would_hold_from(pieces, name, as_of):
    """The first day the rung would hold with no new piece (when a failure leaves the window), or None."""
    _, hours, minimum, days = rung_row(name)
    for ahead in range(1, LOOK_AHEAD + 1):
        d = as_of + dt.timedelta(days=ahead)
        if horizon.rung_holds(pieces, hours, minimum, d, days):
            return d
    return None


def explain(pieces, as_of):
    """The lines printed for one person in one domain."""
    rung = horizon.horizon(pieces, as_of)
    recent = [r for r in pieces if r["date"] > as_of - dt.timedelta(days=horizon.GAIN_WINDOW)]
    g = horizon.gain(recent)
    counted = horizon.rung_pieces(pieces, rung, as_of)
    v, n = sum(map(horizon.verified, counted)), len(counted)
    lines = []
    names = [r[0] for r in horizon.RUNGS]                     # from the top down
    if rung != "below Hour":
        _, hours, minimum, days = rung_row(rung)
        lines.append(f"  {rung} holds: {v} of {n} pieces of at least {hours:g} h in the last {days} days verified; "
                     f"{passes_needed(n)} needed.")
        if v == n:
            lines.append(f"    {v} of {n} is consistent with a true pass rate as low as "
                         f"{one_sided_lower(v, n):.0%} (one-sided 95%).")
        else:
            low, high = exact_interval(v, n)
            lines.append(f"    {v} of {n} is consistent with a true pass rate from {low:.0%} to {high:.0%} (exact 95%).")
        absorb = next(f for f in range(n + 1) if v / (n + f + 1) < horizon.PASS_SHARE)
        planted = (" and none with a missed planted error (from Week up a single missed planted error, in a piece of"
                   " any size, blocks the rung)") if hours >= horizon.PLANTED_FROM else ""
        lines.append("    Slack: " + ("no further failed piece of this size can be absorbed now." if absorb == 0 else
                                       f"{absorb} more failed {'piece' if absorb == 1 else 'pieces'} of this size can be"
                                       f" absorbed now, none of them irreversible (every irreversible piece must pass)"
                                       f"{planted}."))
        last, why = holds_through(pieces, rung, as_of)
        if last is None:
            lines.append(f"    If nothing new is logged, {rung} holds for at least {LOOK_AHEAD} days.")
        else:
            nxt = last + dt.timedelta(days=1)
            gone = leaving(pieces, rung, nxt)
            left = (f"the {'piece' if len(gone) == 1 else 'pieces'} closed {', '.join(gone)} "
                    f"{'leaves' if len(gone) == 1 else 'leave'} the window, and ") if gone else ""
            lines.append(f"    If nothing new is logged, {rung} holds through {last}; on {nxt} {left}"
                         + "; ".join(why) + ".")
        above = names[names.index(rung) - 1] if names.index(rung) > 0 else None
    else:
        above = "Hour"
    if above:
        _, hours, minimum, days = rung_row(above)
        reasons = unmet(pieces, hours, minimum, as_of, days)
        lines.append(f"  {above} needs: " + "; ".join(reasons) + ".")
        back = would_hold_from(pieces, above, as_of)
        if back:
            lines.append(f"    With no new piece, {above} would hold from {back}, when what blocks it leaves the window.")
    else:
        lines.append("  Quarter is the top rung.")
    if g is None:
        lines.append("  Gain: no attention logged in the last 91 days.")
    else:
        done = sum(float(r["reference_hours"]) for r in recent if horizon.verified(r) and not r["outside_help"])
        spent = sum(float(r["attention_minutes"]) for r in recent) / 60.0
        higher = [s for s in horizon.GAIN_STEPS if s > g]
        nxt = f"; the next step, x{min(higher)}, needs a gain of {min(higher)}" if higher else ""
        lines.append(f"  Gain {g:.2f} ({horizon.step(g)}): {done:g} verified reference hours for {spent:.1f} hours of "
                     f"attention in the last 91 days, failures included{nxt}.")
    return rung, v, n, g, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Explain a rung: reasons, slack and what the next rung needs.")
    ap.add_argument("log", help="work log: .jsonl (Appendix C1) or .csv (templates/work-log.csv)")
    ap.add_argument("--as-of", type=record_card.iso_date, default=dt.date.today())
    ap.add_argument("--person", help="only this pseudonymous label")
    args = ap.parse_args(argv)
    as_of = args.as_of
    longest = max(days for *_, days in horizon.RUNGS)
    groups = defaultdict(list)
    for r in record_card.load_any(args.log):
        if as_of - dt.timedelta(days=longest) < r["date"] <= as_of and args.person in (None, r["person"]):
            groups[(r["person"], r["domain"])].append(r)
    quarter = f"{as_of.year}-Q{(as_of.month - 1) // 3 + 1}"
    if not groups:
        print("no pieces in the window")
    for (person, domain), pieces in sorted(groups.items()):
        rung, v, n, g, lines = explain(pieces, as_of)
        print(f"{person}: {domain} . {rung} ({v}/{n}) . {horizon.step(g)} . {quarter}")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
