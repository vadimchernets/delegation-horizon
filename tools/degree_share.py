#!/usr/bin/env python3
"""degree_share.py: what share of your own job postings require a degree, and how often an
alternative to the degree is accepted.

Teaches: Section 6.2 reads the credential crossover point partly from postings. Anyone with an export
of postings (their own company's, a job board download, a scraped sample they are allowed to use) can
measure the same thing: the share that requires a degree, the share that accepts "or equivalent
experience", and the share that does not mention a degree at all, overall and by a grouping column
such as month or job family.
Limits: the patterns are English and deliberately plain; read the sample it prints (--show) before
trusting the shares, and add patterns for your market. A posting is not a hire (Section 6.2).
Usage:
  python3 tools/degree_share.py postings.csv --text description [--by month] [--show 5]
Licence: MIT
"""
import argparse
import csv
import re
import sys
from collections import defaultdict

DEGREE = re.compile(
    r"\b(bachelor'?s?|master'?s?|b\.?\s?s\.?c?|b\.?\s?a\.?|m\.?\s?s\.?c?|ph\.?\s?d|undergraduate|"
    r"(college|university|four[- ]year|4[- ]year)\s+degree|degree\s+(in|required)|"
    r"degree\s+from|degree(?!\s+of\b))\b", re.I)
ALTERNATIVE = re.compile(
    r"\b(or\s+(equivalent|comparable|relevant)\s+(practical\s+|work\s+|professional\s+)?(experience|training)|"
    r"equivalent\s+(practical\s+|work\s+)?experience|degree\s+(is\s+)?(not\s+required|optional|preferred)|"
    r"no\s+degree\s+(is\s+)?required|or\s+equivalent)\b", re.I)


def classify(text):
    """Return one of: required, alternative_accepted, not_mentioned."""
    if not DEGREE.search(text or ""):
        return "not_mentioned"
    return "alternative_accepted" if ALTERNATIVE.search(text) else "required"


def summarise(rows, text_col, by_col=None):
    counts = defaultdict(lambda: defaultdict(int))
    for row in rows:
        group = row.get(by_col, "") if by_col else "all"
        counts[group][classify(row.get(text_col, ""))] += 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="Share of postings that require a degree.")
    ap.add_argument("postings", help="CSV export of postings")
    ap.add_argument("--text", required=True, help="column holding the posting text")
    ap.add_argument("--by", help="optional grouping column, for example month or job family")
    ap.add_argument("--show", type=int, default=0, help="print this many matched snippets per class")
    ap.add_argument("--out", help="optional CSV with one row per group")
    args = ap.parse_args()
    csv.field_size_limit(10 ** 8)
    with open(args.postings, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or args.text not in rows[0]:
        sys.exit(f"no column named {args.text!r} in {args.postings}")
    counts = summarise(rows, args.text, args.by)
    classes = ["required", "alternative_accepted", "not_mentioned"]
    table = []
    for group in sorted(counts):
        c = counts[group]
        n = sum(c.values())
        table.append([group, n] + [f"{c[k] / n:.1%}" for k in classes])
    header = [args.by or "group", "postings"] + [f"share_{k}" for k in classes]
    print("\t".join(header))
    for line in table:
        print("\t".join(map(str, line)))
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(table)
    if args.show:
        shown = defaultdict(int)
        for row in rows:
            text = row.get(args.text, "")
            kind = classify(text)
            m = DEGREE.search(text)
            if m and shown[kind] < args.show:
                shown[kind] += 1
                print(f"[{kind}] ...{text[max(0, m.start() - 60): m.end() + 80]}...")


if __name__ == "__main__":
    main()
