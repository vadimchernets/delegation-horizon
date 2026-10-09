#!/usr/bin/env python3
"""liveness.py: is each product in a frozen sample still alive on a given date?

Teaches: how prediction F27 (Table A6) is scored. A sample of agent-built products is frozen first
(a CSV with name and url), and the same test is applied to every product at every scoring date, so
nobody chooses after the fact which products count. A product is "alive" when its address answers
with a success code; for a GitHub repository it must also have been pushed to within --max-days.
Limits: an answering page is not a used product. Treat the result as the first filter of a
hand check, and keep the output files: the series of dated CSVs is the evidence.
Usage:
  python3 tools/liveness.py sample.csv --out liveness-2027-10-09.csv [--max-days 180] [--timeout 15]
sample.csv columns: name,url (more columns are kept as they are).
No API keys. GitHub's public API allows about 60 unauthenticated calls an hour.
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request

AGENT = "delegation-horizon-liveness/1.0 (research; +https://github.com/vadimchernets/delegation-horizon)"
GITHUB = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?$")


def fetch(url, timeout):
    """Return (status code, body bytes); network errors become status 0."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(200000)
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b""


def check(url, today, max_days, timeout):
    """Return a dict with status, last_push (GitHub only) and alive."""
    m = GITHUB.match(url.strip())
    if m:
        status, body = fetch(f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}", timeout)
        pushed = ""
        alive = False
        if status == 200:
            data = json.loads(body.decode("utf-8") or "{}")
            pushed = (data.get("pushed_at") or "")[:10]
            archived = bool(data.get("archived"))
            if pushed:
                age = (today - dt.date.fromisoformat(pushed)).days
                alive = age <= max_days and not archived
        return {"status": status, "last_push": pushed, "alive": "yes" if alive else "no"}
    status, _ = fetch(url, timeout)
    return {"status": status, "last_push": "", "alive": "yes" if 200 <= status < 400 else "no"}


def main():
    ap = argparse.ArgumentParser(description="Check a frozen sample of products for liveness.")
    ap.add_argument("sample", help="CSV with at least the columns name,url")
    ap.add_argument("--out", required=True, help="CSV to write (one row per product, dated)")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--max-days", type=int, default=180, help="a GitHub repo must be pushed within this many days")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.as_of)
    with open(args.sample, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or not {"name", "url"} <= set(rows[0]):
        sys.exit("the sample needs the columns name and url")
    fields = list(rows[0]) + ["checked", "status", "last_push", "alive"]
    alive = 0
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            result = check(row["url"], today, args.max_days, args.timeout)
            alive += result["alive"] == "yes"
            w.writerow({**row, "checked": today.isoformat(), **result})
    print(f"{alive} of {len(rows)} alive on {today.isoformat()} ({alive / len(rows):.0%}); written to {args.out}")


if __name__ == "__main__":
    main()
