#!/usr/bin/env python3
"""freeze_sample.py: draw the sample of prediction F27 by a rule nobody can steer, and seal it.

Teaches: F27 (Table A6) scores "a sample of at least 300 public products built mainly with coding agents, launched
October to December 2026, frozen on Zenodo by 31 December 2026"; without a frozen sample it is unresolved. A sample
drawn by hand, or by a seed known while the candidates are collected, could be chosen to make the prediction come
true or fail. So the draw follows "commit, then reveal", as risk-limiting election audits do: (1) the candidates are
collected and closed; (2) `--digest` prints the SHA-256 of the eligible pool, which is registered on OSF; (3) only
then is the key revealed: the randomness of a public beacon round (drand) published after that registration, whose
round number the protocol names in advance. Each candidate's key is SHA-256("pool digest:beacon:address"), and each
stratum gives the candidates with the smallest keys. Nobody knows a key while collecting, and changing the list after
the registration changes the pool digest that was registered. The result does not depend on the order of the
candidates file or on the version of Python.
Limits: it trusts the evidence column; whether a product was built mainly with coding agents is decided by the
protocol and the person who collected the candidates. Among rows that name the same address it keeps the one
launched first. One address per product: scheme, case, www, a trailing slash, a fragment and tracking parameters do
not count; on GitHub only owner/repository counts (.git, /tree/..., /commit/..., ?tab=... do not), and an address
without a scheme gets https://. The frozen file carries that one spelling, so tools/liveness.py sees what was drawn.
Usage:
  python3 tools/freeze_sample.py candidates.csv --digest            # step 1: the pool digest to register
  python3 tools/freeze_sample.py candidates.csv --beacon <randomness of the named drand round> \
      --per-stratum 100 --out f27-sample.csv                          # step 2, after the round is published
  python3 tools/freeze_sample.py --check f27-sample.csv --sha256 <the hash printed when it was frozen>
candidates.csv columns: name, url, stratum, launched (YYYY-MM-DD), evidence; other columns are kept.
The frozen file is read by tools/liveness.py (columns name and url) on every scoring date.
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

NEED = ["name", "url", "stratum", "launched", "evidence"]
WINDOW = ("2026-10-01", "2026-12-31")      # F27: launched October to December 2026
MINIMUM = 300                              # F27: at least 300 products
TRACKING = ("utm_", "ref", "source", "fbclid", "gclid")


DATE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")


def parse_date(text):
    """YYYY-MM-DD (or YYYYMMDD) the same way on every Python: date.fromisoformat accepts more forms from 3.11 on."""
    m = DATE.fullmatch(text.strip())
    if not m:
        raise ValueError(f"not a date: {text!r}")
    return dt.date(*map(int, m.groups()))


def with_scheme(url):
    url = url.strip()
    return url if "://" in url else "https://" + url


def normal_url(url):
    """One spelling per address: no scheme, host in lower case without www, no trailing slash, no fragment, no
    tracking parameters; on GitHub the owner and repository only, in lower case, without .git."""
    parts = urllib.parse.urlsplit(with_scheme(url))
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    if host == "github.com":
        segs = [s for s in path.lower().split("/") if s][:2]
        if segs and segs[-1].endswith(".git"):
            segs[-1] = segs[-1][:-4]
        return host + "/" + "/".join(segs)
    query = sorted((k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
                   if not k.lower().startswith(TRACKING))
    return host + path + ("?" + urllib.parse.urlencode(query) if query else "")


def written_url(url):
    """The address as the frozen file carries it: https:// and the one spelling of normal_url."""
    return "https://" + normal_url(url)


def pool_digest(rows):
    """SHA-256 of the eligible pool, independent of row order: one line 'stratum<TAB>address' per candidate."""
    lines = sorted(f"{r['stratum'].strip()}\t{normal_url(r['url'])}" for r in rows)
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def key(seed, url):
    """seed is 'pool digest:beacon'."""
    return hashlib.sha256(f"{seed}:{normal_url(url)}".encode("utf-8")).hexdigest()


def read_candidates(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            rows = list(reader)
    except OSError as e:
        raise ValueError(f"cannot read {path}: {e.strerror}")
    missing = [c for c in NEED if c not in fields]
    if missing:
        raise ValueError(f"{path} lacks the column(s) {', '.join(missing)} (needed: {', '.join(NEED)})")
    return fields, rows


def eligible(rows, start, end):
    """The rows the protocol admits, and a count of the others by reason."""
    left_out, kept = Counter(), []
    for r in rows:
        try:
            launched = parse_date(r["launched"])
        except ValueError:
            left_out["launch date not a date"] += 1
            continue
        if not start <= launched <= end:
            left_out[f"launched outside {start.isoformat()} to {end.isoformat()}"] += 1
        elif not r["evidence"].strip():
            left_out["no evidence"] += 1
        elif not r["url"].strip() or not r["stratum"].strip():
            left_out["no address or no stratum"] += 1
        else:
            kept.append(r)
    by_address = defaultdict(list)
    for r in kept:
        by_address[normal_url(r["url"])].append(r)
    unique = []
    for same in by_address.values():
        same.sort(key=lambda r: (parse_date(r["launched"]), r["name"], r["url"]))
        unique.append(same[0])
        if len(same) > 1:
            left_out["same address as another row"] += len(same) - 1
    return unique, left_out


def draw(rows, seed, per_stratum=None, total=None):
    keyed = sorted(rows, key=lambda r: (r["stratum"].strip(), key(seed, r["url"])))
    if total is not None:
        if total > len(rows):
            raise ValueError(f"--total {total} asks for more than the {len(rows)} eligible candidates")
        chosen = sorted(rows, key=lambda r: key(seed, r["url"]))[:total]
        return sorted(chosen, key=lambda r: (r["stratum"].strip(), key(seed, r["url"])))
    strata = defaultdict(list)
    for r in keyed:
        strata[r["stratum"].strip()].append(r)
    short = {s: len(rs) for s, rs in strata.items() if len(rs) < per_stratum}
    if short:
        raise ValueError("too few eligible candidates for --per-stratum " + str(per_stratum) + ": " +
                         ", ".join(f"{s} has {n}" for s, n in sorted(short.items())))
    return [r for s in sorted(strata) for r in strata[s][:per_stratum]]


def canonical(fields, rows):
    """The sample as bytes: the needed columns first, the others after, LF line ends, UTF-8 without a mark."""
    order = NEED + [f for f in fields if f not in NEED]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(order)
    for r in rows:
        w.writerow([written_url(r["url"]) if c == "url" else (r.get(c) or "").strip() for c in order])
    return buf.getvalue().encode("utf-8")


def sha_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def freeze(args):
    start, end = (parse_date(d) for d in (args.start, args.end))
    fields, rows = read_candidates(args.candidates)
    pool, left_out = eligible(rows, start, end)
    digest = pool_digest(pool)
    if args.digest:
        print(f"{len(rows)} candidates, {len(pool)} eligible")
        for reason, n in sorted(left_out.items()):
            print(f"  left out, {reason}: {n}")
        print(f"pool digest {digest}")
        print(f"candidates file sha256 {sha_file(args.candidates)}")
        print(f"freeze_sample.py sha256 {sha_file(__file__)}")
        print("Register these on OSF; then wait for the beacon round named in the protocol and draw with --beacon.")
        return
    if not args.beacon:
        raise ValueError("give --beacon: the randomness of the public beacon round named in the protocol, published "
                         "after the pool digest was registered (run --digest first)")
    if (args.per_stratum is None) == (args.total is None):
        raise ValueError("give --per-stratum or --total (one of them)")
    seed = f"{digest}:{args.beacon.strip().lower()}"
    sample = draw(pool, seed, args.per_stratum, args.total)
    if len(sample) < args.min:
        raise ValueError(f"the sample has {len(sample)} products; F27 needs at least {args.min} (--min 0 to draw "
                         "a smaller sample for a trial run)")
    data = canonical(fields, sample)
    with open(args.out, "wb") as fh:
        fh.write(data)
    counts = Counter(r["stratum"].strip() for r in sample)
    print(f"{len(rows)} candidates, {len(pool)} eligible; pool digest {digest}; beacon {args.beacon.strip().lower()}")
    for reason, n in sorted(left_out.items()):
        print(f"  left out, {reason}: {n}")
    for s in sorted(counts):
        print(f"  {s}: {counts[s]} drawn of {sum(r['stratum'].strip() == s for r in pool)} eligible")
    print(f"{len(sample)} products written to {args.out}")
    print(f"candidates file sha256 {sha_file(args.candidates)}; freeze_sample.py sha256 {sha_file(__file__)}")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}  (register this on OSF with the Zenodo DOI by 31 December 2026)")


def check(args):
    if not args.sha256:
        raise ValueError("give --sha256: the hash printed when the sample was frozen")
    try:
        with open(args.check, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
    except OSError as e:
        raise ValueError(f"cannot read {args.check}: {e.strerror}")
    if digest != args.sha256.strip().lower():
        raise ValueError(f"{args.check} is not the frozen sample: its sha256 is {digest}")
    print(f"{args.check} is the frozen sample (sha256 {digest})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draw the F27 sample by a key revealed after the pool is registered.",
                                 epilog="See the docstring of this file and kits/f27-sample.md.")
    ap.add_argument("candidates", nargs="?", help="CSV of candidates (name, url, stratum, launched, evidence)")
    ap.add_argument("--digest", action="store_true", help="print the pool digest to register, and draw nothing")
    ap.add_argument("--beacon", help="randomness of the beacon round named in the protocol (hex), published after "
                    "the pool digest was registered")
    ap.add_argument("--per-stratum", type=int, help="products drawn from each stratum")
    ap.add_argument("--total", type=int, help="products drawn from all strata together")
    ap.add_argument("--min", type=int, default=MINIMUM, help="refuse a smaller sample (default 300, as F27 asks)")
    ap.add_argument("--from", dest="start", default=WINDOW[0], help="first launch date admitted (default 2026-10-01)")
    ap.add_argument("--to", dest="end", default=WINDOW[1], help="last launch date admitted (default 2026-12-31)")
    ap.add_argument("--out", help="the frozen sample to write")
    ap.add_argument("--check", help="a sample file to compare with --sha256")
    ap.add_argument("--sha256", help="the hash printed when the sample was frozen")
    args = ap.parse_args(argv)
    try:
        if args.check:
            check(args)
        elif not args.candidates or not (args.out or args.digest):
            raise ValueError("give a candidates file and --out, or --check with --sha256")
        else:
            freeze(args)
    except ValueError as e:
        sys.exit(f"freeze_sample.py: {e}")


if __name__ == "__main__":
    main()
