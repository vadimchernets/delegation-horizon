#!/usr/bin/env python3
"""archive_urls.py: give every source in sources/claims.csv a dated copy in the Internet Archive.

Teaches: a paper about a fast market cites press releases, postings and blog posts that change or
vanish within months. Each claim row keeps the original URL and an archived copy, so a reader can see
what the page said on the date it was cited. Rows that already have an archive_url are left alone.
Limits: the Internet Archive may refuse pages behind paywalls or logins, and its free save service is
rate-limited; rows it could not save keep an empty archive_url and are retried next run.
Usage:
  python3 tools/archive_urls.py sources/claims.csv [--check-only] [--pause 10]
--check-only looks up the newest existing copy without asking for a new one.
No API key. Runs monthly in .github/workflows/archive-sources.yml.
Licence: MIT
"""
import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request

AGENT = "delegation-horizon-archiver/1.0 (research)"


def latest_copy(url, timeout=30):
    """Return the newest archived copy of url, or an empty string."""
    api = "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": url})
    try:
        with urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": AGENT}), timeout=timeout) as r:
            snap = json.loads(r.read().decode("utf-8")).get("archived_snapshots", {}).get("closest", {})
            return snap.get("url", "") if snap.get("available") else ""
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def save_copy(url, timeout=120):
    """Ask the Internet Archive to save url now; return the copy's address or an empty string."""
    try:
        req = urllib.request.Request("https://web.archive.org/save/" + url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            return final if "/web/" in final else ""
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def main():
    ap = argparse.ArgumentParser(description="Archive the URLs of a claims register.")
    ap.add_argument("claims", help="CSV with the columns url and archive_url")
    ap.add_argument("--check-only", action="store_true", help="only look up existing copies")
    ap.add_argument("--pause", type=float, default=10.0, help="seconds between save requests")
    args = ap.parse_args()
    with open(args.claims, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, list(reader)
    if not fields or "url" not in fields or "archive_url" not in fields:
        raise SystemExit("the register needs the columns url and archive_url")
    done = 0
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url.startswith("http") or (row.get("archive_url") or "").strip():
            continue
        copy = latest_copy(url) if args.check_only else (save_copy(url) or latest_copy(url))
        if copy:
            row["archive_url"] = copy
            done += 1
        print(("archived " if copy else "not yet  ") + url)
        if not args.check_only:
            time.sleep(args.pause)
    with open(args.claims, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{done} new archive link(s) written to {args.claims}")


if __name__ == "__main__":
    main()
