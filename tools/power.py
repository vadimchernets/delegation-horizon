#!/usr/bin/env python3
"""power.py: how many people a comparison of pass shares needs, and what a given number of people can show.

Teaches: the arithmetic behind the sample sizes of the paper. Section 11.2 runs the experiments of F2, F3 and F3b
with 1,500 people per group because that gives about 0.8 power to detect a true advantage of 5 points (two-sided
alpha 0.05), where 400 per group would show it only about 30% of the time; the matched-task kit's 400 per group
give an interval of about plus or minus 6 points. The same arithmetic sizes the comparison of Section 10.5.
  --n with --diff      power to detect a true difference of diff;
  --power with --diff  people per group for that power;
  --n alone            half-width of the 95% interval of the difference;
  --n with --margin    chance that the interval's lower bound clears minus margin when there is no true
                       difference (the parity rule of F2).
Limits: a normal approximation for two independent groups of equal size, one pass or fail per person; clustered
data (several pieces per person) need more people, and a registered study states its own calculation.
Usage:
  python3 tools/power.py --p 0.5 --diff 0.05 --n 1500
  python3 tools/power.py --p 0.5 --diff 0.05 --power 0.8
  python3 tools/power.py --p 0.7 --n 400 [--margin 0.10]
Licence: MIT
"""
import argparse
import math
from statistics import NormalDist

Z = NormalDist()


def se(p1, p2, n):
    return math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)


def power(p, diff, n, alpha=0.05):
    """Chance that a two-sided test at alpha detects a true difference diff from a pass share p, n per group."""
    z = Z.inv_cdf(1 - alpha / 2)
    shift = diff / se(p, p + diff, n)
    return Z.cdf(shift - z) + Z.cdf(-shift - z)


def n_for_power(p, diff, target=0.8, alpha=0.05):
    """People per group for the target power (rounded up)."""
    z = Z.inv_cdf(1 - alpha / 2) + Z.inv_cdf(target)
    return math.ceil(z * z * (p * (1 - p) + (p + diff) * (1 - p - diff)) / diff ** 2)


def half_width(p, n, alpha=0.05):
    """Half-width of the interval of the difference of two pass shares near p, n per group."""
    return Z.inv_cdf(1 - alpha / 2) * se(p, p, n)


def parity_chance(p, margin, n, diff=0.0, alpha=0.05):
    """Chance that the lower bound of the interval for (group minus comparison) lies above minus margin."""
    return Z.cdf((diff + margin) / se(p, p + diff, n) - Z.inv_cdf(1 - alpha / 2))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Power and sample size for comparing two pass shares.")
    ap.add_argument("--p", type=float, required=True, help="pass share of the comparison group, 0 to 1")
    ap.add_argument("--diff", type=float, help="true difference to detect, in share points (0.05 is 5 points)")
    ap.add_argument("--n", type=int, help="people per group")
    ap.add_argument("--power", type=float, help="target power, for example 0.8")
    ap.add_argument("--margin", type=float, help="parity margin, for example 0.10 for minus 10 points")
    ap.add_argument("--alpha", type=float, default=0.05)
    a = ap.parse_args(argv)
    if not 0 < a.p < 1:
        ap.error("--p is a pass share strictly between 0 and 1")
    if a.n is not None and a.n < 1:
        ap.error("--n is a number of people per group, 1 or more")
    if not 0 < a.alpha < 1:
        ap.error("--alpha lies strictly between 0 and 1")
    if a.power is not None and not 0 < a.power < 1:
        ap.error("--power lies strictly between 0 and 1")
    if a.margin is not None and not 0 < a.margin < 1:
        ap.error("--margin is a share, for example 0.10 for 10 points")
    if a.diff is not None and (a.diff == 0 or not 0 < a.p + a.diff < 1):
        ap.error("--diff must be non-zero and keep the other group's pass share strictly between 0 and 1")
    if a.diff is not None and a.power is not None:
        print(f"{n_for_power(a.p, a.diff, a.power, a.alpha)} per group for power {a.power:.2f} to detect "
              f"{a.diff * 100:+.1f} points from {a.p:.2f} (two-sided alpha {a.alpha})")
    elif a.diff is not None and a.n:
        print(f"power {power(a.p, a.diff, a.n, a.alpha):.2f} to detect {a.diff * 100:+.1f} points from {a.p:.2f} "
              f"with {a.n} per group (two-sided alpha {a.alpha})")
    elif a.n and a.margin is not None:
        print(f"chance {parity_chance(a.p, a.margin, a.n, alpha=a.alpha):.3f} that the lower bound clears "
              f"-{a.margin * 100:.0f} points when there is no true difference ({a.n} per group, pass share {a.p:.2f})")
    elif a.n:
        print(f"95% interval of the difference: about plus or minus {half_width(a.p, a.n, a.alpha) * 100:.1f} points "
              f"with {a.n} per group at a pass share of {a.p:.2f}")
    else:
        ap.error("give --n, or --diff with --n or --power")


if __name__ == "__main__":
    main()
