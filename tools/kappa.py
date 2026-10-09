#!/usr/bin/env python3
"""kappa.py: agreement of two coders, with the list of items they disagree on.

Teaches: Section 9 codes programmers' conversations into categories (kits/coding-codebook.md), and a
coding is only worth its agreement. This prints percent agreement, Cohen's kappa, the confusion table
and writes the disagreements to a CSV for the reconciliation meeting.
Limits: Cohen's kappa for two coders and one code per item. For more coders or multiple codes per
item use Krippendorff's alpha. A high kappa on a codebook that misses the point is still a miss.
Usage:
  python3 tools/kappa.py codes.csv --a coder_a --b coder_b [--id item] [--disagreements out.csv]
Licence: MIT
"""
import argparse
import csv
import sys
from collections import Counter


def cohen_kappa(a, b):
    """Return (observed agreement, kappa) for two equal-length lists of labels."""
    if len(a) != len(b) or not a:
        raise ValueError("two non-empty lists of the same length are needed")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1:
        return observed, 1.0
    return observed, (observed - expected) / (1 - expected)


def band(k):
    """Landis and Koch (1977) wording, the usual reference point."""
    for limit, word in [(0.8, "almost perfect"), (0.6, "substantial"), (0.4, "moderate"),
                        (0.2, "fair"), (0.0, "slight")]:
        if k > limit:
            return word
    return "poor"


def main():
    ap = argparse.ArgumentParser(description="Cohen's kappa for two coders.")
    ap.add_argument("codes", help="CSV with one row per item and one column per coder")
    ap.add_argument("--a", required=True, help="column of the first coder")
    ap.add_argument("--b", required=True, help="column of the second coder")
    ap.add_argument("--id", default="", help="column identifying the item (default: row number)")
    ap.add_argument("--disagreements", help="CSV to write the items the coders disagree on")
    args = ap.parse_args()
    with open(args.codes, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get(args.a) or "").strip() and (r.get(args.b) or "").strip()]
    if not rows:
        sys.exit("no rows coded by both coders")
    a = [r[args.a].strip() for r in rows]
    b = [r[args.b].strip() for r in rows]
    observed, k = cohen_kappa(a, b)
    print(f"items coded by both: {len(rows)}")
    print(f"percent agreement: {observed:.1%}")
    print(f"Cohen's kappa: {k:.3f} ({band(k)})")
    labels = sorted(set(a) | set(b))
    pairs = Counter(zip(a, b))
    print("\nconfusion (rows: " + args.a + ", columns: " + args.b + ")")
    print("\t" + "\t".join(labels))
    for x in labels:
        print(x + "\t" + "\t".join(str(pairs[(x, y)]) for y in labels))
    if args.disagreements:
        with open(args.disagreements, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["item", args.a, args.b, "agreed_code", "note"])
            for i, (r, x, y) in enumerate(zip(rows, a, b), 1):
                if x != y:
                    w.writerow([r.get(args.id, i) if args.id else i, x, y, "", ""])
        print(f"\ndisagreements written to {args.disagreements}")


if __name__ == "__main__":
    main()
