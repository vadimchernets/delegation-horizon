"""Tests for tools/guarantor_record.py: the guarantor's record of Section 7.2, computed from a ledger.
Standard library only: python3 -m unittest tests.test_guarantor_record"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "guarantor_record.py"
LEDGER = ROOT / "examples" / "guarantor-ledger.csv"
EXPECTED = ROOT / "examples" / "guarantor-expected.txt"
sys.path.insert(0, str(ROOT / "tools"))
import guarantor_record as gr  # noqa: E402

HEAD = ["guarantor", "domain", "product", "maker", "vouched_on", "status", "ended_on", "severity"]


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True,
                          cwd=ROOT, timeout=60)


def ledger(folder, rows, name="ledger.csv"):
    path = Path(folder) / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    return path


class WorkedExample(unittest.TestCase):
    def test_prints_the_expected_lines(self):
        r = run(LEDGER, "--as-of", "2026-10-09")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, EXPECTED.read_text(encoding="utf-8"))

    def test_numbers_worked_by_hand(self):
        # ages on 2026-10-09: 403, 328, 272, 250, 203, 157, 101, 55, 14 days. Six months (182 days) old or more:
        # the first five, of which the fourth (withdrawn after 42 days) did not live 182 days: 4 of 5. Twelve months
        # (365 days): only the first, still live: 1 of 1. Lives of the products that ended: 228, 42 and 92 days.
        s = gr.summarise(gr.load(str(LEDGER)), gr.dt.date(2026, 10, 9))[0]
        self.assertEqual((s["vouched"], s["live_6"], s["eligible_6"], s["live_12"], s["eligible_12"]), (9, 4, 5, 1, 1))
        self.assertEqual(s["severity"], {"minor": 2, "harmful": 1, "severe": 0})
        self.assertEqual(s["median_ended"], 92)
        self.assertEqual(s["status"], {"live": 6, "retired": 2, "withdrawn": 1})

    def test_weights_give_one_number_only_when_asked(self):
        r = run(LEDGER, "--as-of", "2026-10-09", "--weights", "minor=1,harmful=3,severe=10")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("weighted failures 5 (minor 1, harmful 3, severe 10)", r.stdout)
        self.assertNotIn("weighted", run(LEDGER, "--as-of", "2026-10-09").stdout)

    def test_a_later_date_moves_the_counts(self):
        r = run(LEDGER, "--as-of", "2026-12-31")
        self.assertEqual(r.returncode, 0, r.stderr)
        # 2026-12-31: six months old or more are the first seven (the seventh, vouched 2026-06-30, is 184 days old);
        # the fourth (42 days) and the seventh (retired after 92 days) did not live 182 days: 5 of 7
        self.assertIn("live at 6 months 5/7", r.stdout)


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_guarantors_and_two_domains_are_kept_apart(self):
        rows = [["G01", "law", "a", "M1", "2026-01-01", "live", "", "none"],
                ["G01", "bookkeeping", "b", "M2", "2026-01-01", "retired", "2026-02-01", "severe"],
                ["G02", "law", "c", "M3", "2026-01-01", "live", "", "none"]]
        r = run(ledger(self.dir, rows), "--as-of", "2026-10-09")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [x for x in r.stdout.splitlines() if not x.startswith("  ")]
        self.assertEqual(lines, [
            "G01: bookkeeping . 1 vouched . live at 6 months 0/1, at 12 months 0/0 . failures 0 minor, 0 harmful, 1 severe . 2026-Q4",
            "G01: law . 1 vouched . live at 6 months 1/1, at 12 months 0/0 . failures 0 minor, 0 harmful, 0 severe . 2026-Q4",
            "G02: law . 1 vouched . live at 6 months 1/1, at 12 months 0/0 . failures 0 minor, 0 harmful, 0 severe . 2026-Q4"])

    def test_six_months_is_182_days_and_twelve_is_365(self):
        as_of = gr.dt.date(2026, 10, 9)
        ago = lambda days: (as_of - gr.dt.timedelta(days=days)).isoformat()   # noqa: E731
        rows = [["G01", "law", "young", "M1", ago(181), "live", "", "none"],              # not yet six months old
                ["G01", "law", "six", "M2", ago(182), "live", "", "none"],                # six months old, alive
                ["G01", "law", "short", "M3", ago(300), "retired", ago(300 - 181), "minor"],   # ended after 181 days
                ["G01", "law", "lived", "M4", ago(300), "retired", ago(300 - 182), "none"],    # ended after 182 days
                ["G01", "law", "year", "M5", ago(365), "live", "", "none"],
                ["G01", "law", "almost", "M6", ago(364), "live", "", "none"]]
        s = gr.summarise(gr.load(str(ledger(self.dir, rows))), as_of)[0]
        self.assertEqual((s["live_6"], s["eligible_6"]), (4, 5))
        self.assertEqual((s["live_12"], s["eligible_12"]), (1, 1))

    def test_products_vouched_after_the_date_are_not_counted(self):
        rows = [["G01", "law", "a", "M1", "2026-01-01", "live", "", "none"],
                ["G01", "law", "b", "M2", "2026-11-01", "live", "", "none"]]
        r = run(ledger(self.dir, rows), "--as-of", "2026-10-09")
        self.assertIn(". 1 vouched .", r.stdout)

    def test_bad_rows_stop_with_one_line(self):
        cases = [
            ([["G01", "law", "a", "M1", "2026-01-01", "sold", "", "none"]], "status"),
            ([["G01", "law", "a", "M1", "2026-01-01", "live", "", "awful"]], "severity"),
            ([["G01", "law", "a", "M1", "2026-01-01", "retired", "", "none"]], "ended_on"),
            ([["G01", "law", "a", "M1", "2026-01-01", "live", "2026-02-01", "none"]], "ended_on"),
            ([["G01", "law", "a", "M1", "2026-03-01", "retired", "2026-02-01", "none"]], "before"),
            ([["G01", "law", "a", "M1", "1 March 2026", "live", "", "none"]], "date"),
        ]
        for i, (rows, needle) in enumerate(cases):
            r = run(ledger(self.dir, rows, f"bad{i}.csv"), "--as-of", "2026-10-09")
            with self.subTest(needle=needle):
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
                self.assertIn(needle, r.stderr)
        missing = self.dir / "cols.csv"
        missing.write_text("guarantor,product\nG01,a\n", encoding="utf-8")
        r = run(missing)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vouched_on", r.stderr)
        r = run(LEDGER, "--weights", "minor=x")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)

    def test_help(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class Template(unittest.TestCase):
    def test_the_template_names_the_tool_and_its_columns(self):
        text = (ROOT / "templates" / "guarantor-record.md").read_text(encoding="utf-8")
        self.assertIn("tools/guarantor_record.py", text)
        for column in HEAD:
            self.assertIn(f"`{column}`", text)


if __name__ == "__main__":
    unittest.main()
