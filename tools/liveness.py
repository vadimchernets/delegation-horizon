#!/usr/bin/env python3
"""liveness.py: is each product in a frozen sample still alive on a given date?

Teaches: how prediction F27 (Table A6) is scored. A sample of agent-built products is frozen first
(a CSV with name and url, tools/freeze_sample.py), and the same test is applied to every product at every
scoring date, so nobody chooses after the fact which products count. F27 counts a product as retired when
it is "unreachable or not updated for 12 months", and this script follows those words and nothing else:
  - unreachable: the address answers 404, 410 or 451, or no server answers at all after the retries;
  - not updated for 12 months: for a GitHub repository, no push within --max-days (365, F27's 12 months).
    Being archived is not in F27's words: it is written in its own column and does not retire a product.
An answer that says nothing about the product (403, 429, 5xx, GitHub's rate limit after the waits) is
"unknown": it is left out of the share and listed for the hand check, never counted as retired.
GitHub's public API allows 60 calls an hour from one address without a key. The script reads an optional
token from the environment (GITHUB_TOKEN, 5,000 calls an hour), and without one it waits for the reset the
API names and goes on, so 100 repositories take under two hours; it says so on the screen while it waits.
Dates: the column checked is the day the script ran; as_of is the scoring date. A push after as_of is
marked "updated after the date" and goes to the hand check against a Wayback Machine snapshot of as_of.
Limits: an answering page is not a used product, and for an address outside GitHub the script cannot see
when the product was last updated: the Wayback Machine snapshots named as F27's fallback source show it.
Treat the result as the first filter of a hand check, and keep the output files: the series of dated CSVs
is the evidence.
Usage:
  python3 tools/liveness.py sample.csv --out liveness-2027-10-09.csv [--as-of 2027-10-09] [--max-days 365]
  GITHUB_TOKEN=... python3 tools/liveness.py f27-sample.csv --out liveness-2028-12-31.csv --as-of 2028-12-31
sample.csv columns: name,url (more columns are kept as they are).
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request

AGENT = "delegation-horizon-liveness/1.1 (research; +https://github.com/vadimchernets/delegation-horizon)"
MAX_DAYS = 365      # F27: retired when "unreachable or not updated for 12 months"
GONE = {404, 410, 451}          # unreachable: the address says the product is not there
RETRIES = 3                     # tries after the first for 403, 429, 5xx and network failures
MAX_WAIT = 3900                 # longest single wait for GitHub's rate limit to reset, in seconds


def pause(seconds):
    time.sleep(seconds)


def github_repo(url):
    """owner/repo when the address is a GitHub repository, written in any of the usual ways; else None."""
    url = url.strip()
    parts = urllib.parse.urlsplit(url if "://" in url else "https://" + url)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "github.com":
        return None
    segs = [s for s in parts.path.split("/") if s][:2]
    if len(segs) < 2:
        return None
    owner, repo = segs
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


def fetch(url, timeout, headers=None):
    """Return (status code, body bytes, response headers); network errors and bad addresses become status 0."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": AGENT, **(headers or {})})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(200000), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, b"", dict(exc.headers or {})
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b"", {}


def wait_for(status, headers, attempt, now=None):
    """Seconds to wait before the next try, from GitHub's rate-limit headers when it gives them."""
    low = {k.lower(): v for k, v in (headers or {}).items()}
    if low.get("retry-after", "").strip().isdigit():
        return min(int(low["retry-after"]), MAX_WAIT)
    if status in (403, 429) and low.get("x-ratelimit-remaining") == "0" and low.get("x-ratelimit-reset", "").isdigit():
        now = time.time() if now is None else now
        return max(1, min(int(low["x-ratelimit-reset"]) - int(now) + 1, MAX_WAIT))
    return 5 * 2 ** attempt


def get(url, timeout, headers=None, retries=RETRIES):
    """fetch with retries for answers that say nothing about the product."""
    for attempt in range(retries + 1):
        res = fetch(url, timeout, headers) if headers else fetch(url, timeout)
        status, body = res[0], res[1]
        hdrs = res[2] if len(res) > 2 else {}
        if status == 200 or (200 <= status < 400) or status in GONE or attempt == retries:
            return status, body
        seconds = wait_for(status, hdrs, attempt)
        if status in (403, 429):
            print(f"  {url}: answer {status} (rate limit or refusal); waiting {seconds} s, try {attempt + 2} of "
                  f"{retries + 1}" + ("" if os.environ.get("GITHUB_TOKEN") else "; set GITHUB_TOKEN to go faster"),
                  file=sys.stderr)
        pause(seconds)
    return status, body


def verdict(status):
    if 200 <= status < 400:
        return "yes"
    if status in GONE or status == 0:
        return "no"
    return "unknown"


def check(url, as_of, max_days, timeout, retries=RETRIES):
    """Return a dict with status, last_push and archived (GitHub only), alive (yes, no, unknown) and note."""
    repo = github_repo(url)
    if repo:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else None
        status, body = get(f"https://api.github.com/repos/{repo}", timeout, headers, retries)
        out = {"status": status, "last_push": "", "archived": "", "alive": verdict(status), "note": ""}
        if status == 200:
            data = json.loads(body.decode("utf-8") or "{}")
            out["last_push"] = (data.get("pushed_at") or "")[:10]
            out["archived"] = "yes" if data.get("archived") else "no"
            if not out["last_push"]:
                out.update(alive="unknown", note="no push date")
            else:
                age = (as_of - dt.date.fromisoformat(out["last_push"])).days
                if age < 0:
                    out.update(alive="unknown", note="updated after the date: hand check of a snapshot of as_of")
                else:
                    out["alive"] = "yes" if age <= max_days else "no"
        elif out["alive"] == "unknown":
            out["note"] = "no usable answer from GitHub: hand check"
        return out
    status, _ = get(url, timeout, None, retries)
    alive = verdict(status)
    return {"status": status, "last_push": "", "archived": "", "alive": alive,
            "note": "hand check: update within 12 months, Wayback Machine" if alive != "no" else ""}


def main():
    ap = argparse.ArgumentParser(description="Check a frozen sample of products for liveness (F27's rule).")
    ap.add_argument("sample", help="CSV with at least the columns name,url")
    ap.add_argument("--out", required=True, help="CSV to write (one row per product, dated)")
    ap.add_argument("--as-of", default=dt.date.today().isoformat(), help="the scoring date (default today)")
    ap.add_argument("--max-days", type=int, default=MAX_DAYS,
                    help="a GitHub repo must be pushed within this many days (default 365: F27's 12 months)")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--retries", type=int, default=RETRIES, help="tries after the first for 403, 429, 5xx (3)")
    args = ap.parse_args()
    as_of = dt.date.fromisoformat(args.as_of)
    with open(args.sample, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or not {"name", "url"} <= set(rows[0]):
        sys.exit("the sample needs the columns name and url")
    if not os.environ.get("GITHUB_TOKEN"):
        print("No GITHUB_TOKEN: GitHub allows 60 calls an hour; the script waits for each reset.", file=sys.stderr)
    fields = list(rows[0]) + ["checked", "as_of", "status", "last_push", "archived", "alive", "note"]
    count = {"yes": 0, "no": 0, "unknown": 0}
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            result = check(row["url"], as_of, args.max_days, args.timeout, args.retries)
            count[result["alive"]] += 1
            w.writerow({**row, "checked": dt.date.today().isoformat(), "as_of": as_of.isoformat(), **result})
    known = count["yes"] + count["no"]
    share = f"{100 * count['no'] / known:.1f}%" if known else "n/a"
    print(f"{count['yes']} of {len(rows)} alive, {count['no']} retired ({share} of the {known} decided), "
          f"{count['unknown']} unknown (hand check) as of {as_of.isoformat()}; written to {args.out}")


if __name__ == "__main__":
    main()
