"""Tests for tools/freeze_sample.py: the frozen sample of prediction F27 (Table A6) and its seal.
Standard library only, no network: python3 -m unittest tests.test_freeze_sample"""
import contextlib
import csv
import hashlib
import io
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "freeze_sample.py"
sys.path.insert(0, str(ROOT / "tools"))
import freeze_sample  # noqa: E402
import liveness  # noqa: E402

HEAD = ["name", "url", "stratum", "launched", "evidence", "note"]
STRATA = ("repositories", "launch-sites", "builder-showcases")


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True,
                          cwd=ROOT, timeout=120)


def candidates(per_stratum=150, extra=True):
    """Eligible rows in three strata, then rows the protocol leaves out."""
    rows = []
    for s in STRATA:
        for i in range(per_stratum):
            day = 1 + i % 28
            month = 10 + i % 3
            rows.append([f"{s} product {i}", f"https://example.org/{s}/{i}", s, f"2026-{month:02d}-{day:02d}",
                         "co-author trailer in 7 of 9 commits" if s == "repositories" else "maker says so", ""])
    if extra:
        rows += [
            ["too early", "https://example.org/early", "repositories", "2026-09-30", "trailer", ""],
            ["too late", "https://example.org/late", "repositories", "2027-01-01", "trailer", ""],
            ["no evidence", "https://example.org/none", "launch-sites", "2026-11-02", "", ""],
            ["not a date", "https://example.org/nodate", "launch-sites", "2 November", "maker says so", ""],
            # the same product twice, written differently
            ["dup", "HTTP://WWW.Example.org/repositories/3/", "repositories", "2026-10-04", "trailer", ""],
            ["dup git", "https://github.com/a/b.git", "repositories", "2026-10-05", "trailer", ""],
            ["dup git 2", "https://github.com/A/b/", "repositories", "2026-10-05", "trailer", ""],
        ]
    return rows


def write(folder, rows, name="candidates.csv"):
    path = Path(folder) / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    return path


def read(path):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Freeze(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self, rows, *extra, name="sample.csv"):
        out = self.dir / name
        r = run(write(self.dir, rows, "c-" + name), "--beacon", "ab12", "--per-stratum", "100", "--out", out, *extra)
        return r, out

    def test_one_hundred_from_each_stratum_and_the_hash_printed(self):
        r, out = self.freeze(candidates())
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = read(out)
        self.assertEqual(len(rows), 300)
        for s in STRATA:
            self.assertEqual(sum(x["stratum"] == s for x in rows), 100)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        self.assertIn(f"sha256 {digest}", r.stdout)
        self.assertIn("beacon ab12", r.stdout)
        self.assertIn("pool digest ", r.stdout)

    def test_the_draw_is_the_smallest_keys_of_each_stratum(self):
        r, out = self.freeze(candidates(extra=False))
        self.assertEqual(r.returncode, 0, r.stderr)
        chosen = {x["url"] for x in read(out)}
        rows = [dict(zip(HEAD, x)) for x in candidates(extra=False)]
        pool = freeze_sample.pool_digest(rows)
        for s in STRATA:
            urls = [row[1] for row in candidates(extra=False) if row[2] == s]
            keyed = sorted(urls, key=lambda u: hashlib.sha256(f"{pool}:ab12:{freeze_sample.normal_url(u)}"
                                                              .encode()).hexdigest())
            with self.subTest(stratum=s):
                self.assertEqual({u for u in keyed[:100]}, {u for u in urls if u in chosen})

    def test_same_seed_same_bytes_whatever_the_order_of_the_candidates(self):
        rows = candidates()
        r1, out1 = self.freeze(rows, name="a.csv")
        shuffled = rows[:]
        random.Random(3).shuffle(shuffled)
        r2, out2 = self.freeze(shuffled, name="b.csv")
        self.assertEqual((r1.returncode, r2.returncode), (0, 0))
        self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_another_seed_draws_another_sample(self):
        r1, out1 = self.freeze(candidates(), name="a.csv")
        out2 = self.dir / "b.csv"
        r2 = run(write(self.dir, candidates(), "c2.csv"), "--beacon", "07", "--per-stratum", "100", "--out", out2)
        self.assertEqual((r1.returncode, r2.returncode), (0, 0))
        self.assertNotEqual({x["url"] for x in read(out1)}, {x["url"] for x in read(out2)})

    def test_rows_outside_the_protocol_are_listed_and_left_out(self):
        r, out = self.freeze(candidates())
        self.assertEqual(r.returncode, 0, r.stderr)
        urls = {x["url"] for x in read(out)}
        for gone in ("https://example.org/early", "https://example.org/late", "https://example.org/none",
                     "https://example.org/nodate", "https://github.com/A/b/"):
            self.assertNotIn(gone, urls)
        for reason in ("launched outside 2026-10-01 to 2026-12-31: 2", "no evidence: 1", "launch date not a date: 1",
                       "same address as another row: 2"):
            self.assertIn(reason, r.stdout)

    def test_a_short_stratum_is_named_and_nothing_is_written(self):
        rows = [x for x in candidates(extra=False) if not (x[2] == "launch-sites" and int(x[1].rsplit("/", 1)[1]) >= 60)]
        r, out = self.freeze(rows)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("launch-sites", r.stderr)
        self.assertIn("60", r.stderr)
        self.assertFalse(out.exists())

    def test_fewer_than_300_is_not_an_f27_sample(self):
        out = self.dir / "small.csv"
        r = run(write(self.dir, candidates()), "--beacon", "01", "--per-stratum", "50", "--out", out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("at least 300", r.stderr)
        self.assertFalse(out.exists())
        r = run(write(self.dir, candidates()), "--beacon", "01", "--per-stratum", "50", "--min", "0", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(read(out)), 150)

    def test_total_instead_of_per_stratum(self):
        out = self.dir / "total.csv"
        r = run(write(self.dir, candidates()), "--beacon", "01", "--total", "320", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(read(out)), 320)

    def test_check_confirms_the_frozen_file_and_catches_a_change(self):
        r, out = self.freeze(candidates())
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        ok = run("--check", out, "--sha256", digest)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("the frozen sample", ok.stdout)
        out.write_bytes(out.read_bytes().replace(b"product 1", b"product 9", 1))
        bad = run("--check", out, "--sha256", digest)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("not the frozen sample", bad.stderr)

    def test_liveness_reads_the_frozen_sample(self):
        r, out = self.freeze(candidates())
        self.assertEqual(r.returncode, 0, r.stderr)
        result = self.dir / "live.csv"
        argv = ["liveness.py", str(out), "--out", str(result), "--as-of", "2028-12-31"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(liveness, "fetch", return_value=(200, b"")), \
                contextlib.redirect_stdout(io.StringIO()):
            liveness.main()
        self.assertEqual(len(read(result)), 300)

    def test_bad_input_exits_with_one_line(self):
        missing = self.dir / "missing.csv"
        cases = [
            (run(missing, "--beacon", "01", "--per-stratum", "1", "--out", self.dir / "o.csv"), "cannot read"),
            (run(write(self.dir, [["a", "https://x.org", "s", "2026-10-02", "e", ""]], "one.csv"),
                 "--per-stratum", "1", "--out", self.dir / "o.csv"), "--beacon"),
            (run(write(self.dir, candidates(), "c3.csv"), "--beacon", "01", "--out", self.dir / "o.csv"),
             "--per-stratum or --total"),
        ]
        no_cols = self.dir / "cols.csv"
        no_cols.write_text("name,url\nx,https://x.org\n", encoding="utf-8")
        cases.append((run(no_cols, "--beacon", "01", "--total", "1", "--min", "0", "--out", self.dir / "o.csv"),
                      "stratum"))
        for r, needle in cases:
            with self.subTest(needle=needle):
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr)
                self.assertIn(needle, r.stderr)

    def test_help(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class CommitThenReveal(unittest.TestCase):
    """Finding of the review of 10 Oct 2026: a seed published before collection let the collector compute every key
    and pick which products to enter. Now the key needs a beacon value revealed after the pool digest is registered."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_digest_prints_what_to_register_and_draws_nothing(self):
        path = write(self.dir, candidates())
        r = run(path, "--digest")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [dict(zip(HEAD, x)) for x in candidates()]
        pool, _ = freeze_sample.eligible(rows, freeze_sample.parse_date("2026-10-01"),
                                         freeze_sample.parse_date("2026-12-31"))
        self.assertIn(f"pool digest {freeze_sample.pool_digest(pool)}", r.stdout)
        self.assertIn(f"candidates file sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}", r.stdout)
        self.assertEqual(list(self.dir.glob("*sample*")), [])

    def test_no_draw_without_a_beacon(self):
        r = run(write(self.dir, candidates()), "--per-stratum", "100", "--out", self.dir / "s.csv")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--beacon", r.stderr)

    def test_adding_one_candidate_changes_every_key(self):
        rows = [dict(zip(HEAD, x)) for x in candidates(extra=False)]
        more = rows + [dict(zip(HEAD, ["new", "https://example.org/new", "repositories", "2026-10-02", "e", ""]))]
        self.assertNotEqual(freeze_sample.pool_digest(rows), freeze_sample.pool_digest(more))

    def test_dates_read_the_same_on_every_python(self):
        self.assertEqual(freeze_sample.parse_date("20261005"), freeze_sample.parse_date("2026-10-05"))
        with self.assertRaises(ValueError):
            freeze_sample.parse_date("2026-W41-1")

    def test_the_frozen_file_carries_one_spelling(self):
        self.assertEqual(freeze_sample.written_url("https://GitHub.com/Acme/Tool/tree/main"),
                         "https://github.com/acme/tool")
        self.assertEqual(freeze_sample.written_url("example.com/app"), "https://example.com/app")


class NormalUrl(unittest.TestCase):
    def test_the_same_address_written_differently(self):
        same = ["https://github.com/a/b", "http://github.com/a/b/", "https://GitHub.com/a/b.git", "https://github.com/A/B",
                "https://www.github.com/a/b?tab=readme#top", "https://github.com/a/b/tree/main",
                "https://github.com/a/b/commit/0123abc", "github.com/a/b"]
        self.assertEqual(len({freeze_sample.normal_url(u) for u in same}), 1)
        self.assertNotEqual(freeze_sample.normal_url("https://example.org/a"),
                            freeze_sample.normal_url("https://example.org/b"))


if __name__ == "__main__":
    unittest.main()
