#!/usr/bin/env python3
"""name_race.py: count, year by year, how often each candidate name appears in scholarly records.

Teaches: Section 3 keeps a dated map of names instead of choosing one, and predictions F9 and N7 are
scored by which names gain ground. This script makes that count repeatable by anyone: exact-phrase
works in OpenAlex and works matching the phrase in Crossref, per name and per year, written to CSV.
Limits: scholarly counts lag job titles and press usage by a year or more, and Crossref matching is
fuzzy (treat its column as an upper bound). A count is a signal of uptake, not of meaning; read a
sample of the hits before drawing a conclusion. Both services are free. Crossref needs no key; OpenAlex
gives a small keyless daily budget per network address and a free personal key for more: put it in the
environment variable OPENALEX_API_KEY (it is read from there and never written to any file).
Usage:
  python3 tools/name_race.py --from 2024 --to 2026 --out names.csv
  python3 tools/name_race.py --names my-names.txt --from 2025 --to 2026 --mailto you@example.org
my-names.txt: one name per line; lines starting with # are skipped.
Licence: MIT
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Candidates from Tables 2a and 2b of the paper (9 October 2026); edit or pass --names to change.
DEFAULT_NAMES = [
    "agentic engineer", "agent manager", "agent boss", "AI orchestrator", "AI operator", "AI steward",
    "product builder", "builder", "vibe coding", "AI fluency", "agent literacy", "acceptance literacy",
    "agentwright", "domain orchestrator", "delegation horizon", "amplification gain",
    "credential crossover", "citizen developer", "guarantor", "tokenmaxxing",
]
AGENT = "delegation-horizon-name-race/1.0 (research)"


WARNED = set()


def get_json(url, timeout=30, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:                      # budget used up: say why once, do not hammer
                host = urllib.parse.urlparse(url).netloc
                if host not in WARNED:
                    WARNED.add(host)
                    detail = exc.read(400).decode("utf-8", "replace")
                    print(f"{host}: rate limit reached ({detail.strip()[:300]})", file=sys.stderr)
                return None
            if attempt == tries - 1:
                return None
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, OSError, ValueError):
            if attempt == tries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def openalex_count(name, year, mailto=""):
    q = {"search": f'"{name}"', "filter": f"publication_year:{year}", "per-page": "1"}
    if mailto:
        q["mailto"] = mailto
    if os.environ.get("OPENALEX_API_KEY"):
        q["api_key"] = os.environ["OPENALEX_API_KEY"]
    data = get_json("https://api.openalex.org/works?" + urllib.parse.urlencode(q))
    return "" if data is None else data.get("meta", {}).get("count", "")


def crossref_count(name, year, mailto=""):
    q = {"query.bibliographic": name, "rows": "0",
         "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31"}
    if mailto:
        q["mailto"] = mailto
    data = get_json("https://api.crossref.org/works?" + urllib.parse.urlencode(q))
    return "" if data is None else data.get("message", {}).get("total-results", "")


def read_names(path):
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]


def main():
    ap = argparse.ArgumentParser(description="Yearly counts of candidate names in OpenAlex and Crossref.")
    ap.add_argument("--names", help="text file, one name per line (default: the paper's tables)")
    ap.add_argument("--from", dest="start", type=int, required=True)
    ap.add_argument("--to", dest="end", type=int, required=True)
    ap.add_argument("--out", default="names.csv")
    ap.add_argument("--mailto", default="", help="optional contact address for the services' polite pools")
    ap.add_argument("--pause", type=float, default=0.2, help="seconds between calls")
    args = ap.parse_args()
    names = read_names(args.names) if args.names else DEFAULT_NAMES
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "year", "openalex_exact_phrase", "crossref_fuzzy"])
        for name in names:
            for year in range(args.start, args.end + 1):
                row = [name, year, openalex_count(name, year, args.mailto), crossref_count(name, year, args.mailto)]
                w.writerow(row)
                print(*row, sep="\t")
                time.sleep(args.pause)
    print(f"written to {args.out} (empty cell = the service did not answer)")


if __name__ == "__main__":
    main()
