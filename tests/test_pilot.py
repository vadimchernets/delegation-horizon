"""Tests for the desk pre-pilot scripts (pilot/). Standard library only: python3 -m unittest"""
import csv
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pilot"))
import table_g2  # noqa: E402
import prolific_to_long as ptl  # noqa: E402
import rater_agreement as ra  # noqa: E402
import screen_compare  # noqa: E402
import simulate_rules as sim  # noqa: E402

DEMO = ROOT / "pilot" / "demo"
SOURCES = [f"bookkeeping={DEMO / 'prolific-demo-bookkeeping.jsonl'}", f"webtools={DEMO / 'prolific-demo-webtools.jsonl'}"]


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=120)


class Binomial(unittest.TestCase):
    def test_day_at_08(self):
        self.assertAlmostEqual(sim.exact(10, 0.8), 0.6778, places=3)

    def test_passes_needed_follow_horizon_share(self):
        self.assertEqual([sim.needed(n, 0.8) for n in (3, 4, 5, 6, 10)], [3, 4, 4, 5, 8])

    def test_v1_month_harder_than_quarter_everywhere(self):
        for p in sim.P_GRID:
            self.assertLess(sim.exact(4, p), sim.exact(3, p))

    def test_v11_month_not_easier_than_quarter_from_06(self):
        for p in sim.P_GRID:
            self.assertGreaterEqual(sim.exact(6, p), sim.exact(3, p))

    def test_v11_ladder_monotone_at_design_point_and_above(self):
        for p in (0.8, 0.9, 0.95):
            day, week, month, quarter = (sim.exact(n, p) for n in (10, 6, 6, 3))
            self.assertTrue(day >= week >= month >= quarter)


class FullRule(unittest.TestCase):
    def test_horizon_scorer_matches_binomial(self):
        import random
        rng = random.Random(1)
        for hours, n, days in ((8.0, 10, 91), (160.0, 4, 365), (500.0, 3, 365)):
            mc = sim.full_rule(rng, 0.8, hours, n, days, 3000)
            self.assertAlmostEqual(mc, sim.exact(n, 0.8), delta=0.035)

    def test_script_writes_results(self):
        with tempfile.TemporaryDirectory() as d:
            sys.argv = ["simulate_rules.py", "--reps", "300", "--out", d]
            sim.main()
            for name in ("operating-characteristic.csv", "month-candidates.csv",
                         "sensitivity-day.csv", "rater-noise-day.csv"):
                self.assertTrue((Path(d) / name).exists(), name)

    def test_rater_noise_boundary(self):
        sigma = math.log(1.5) / 1.2815515655446004 / math.sqrt(2)
        from statistics import NormalDist
        p7 = 1 - NormalDist(0, sigma / math.sqrt(2)).cdf(math.log(8 / 7))
        self.assertAlmostEqual(p7, 0.199, places=2)


class Raters(unittest.TestCase):
    def test_within_and_band(self):
        self.assertTrue(ra.within(2, 3))
        self.assertFalse(ra.within(2, 3.1))
        self.assertEqual(ra.band(8), "Day")
        self.assertEqual(ra.band(0.5), "below Hour")
        self.assertEqual(ra.band(160), "Month")

    def test_icc_perfect_and_noisy(self):
        perfect = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
        self.assertAlmostEqual(ra.icc21(perfect), 1.0)
        noisy = [[1.0, 3.0], [2.0, 1.0], [3.0, 2.0]]
        self.assertLess(ra.icc21(noisy), 0.5)

    def test_summary_from_files(self):
        with tempfile.TemporaryDirectory() as d:
            r, t = os.path.join(d, "r.csv"), os.path.join(d, "t.csv")
            with open(r, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["task_id", "rater", "reference_hours", "confidence"])
                w.writerows([["BK01", "A", 2, "high"], ["BK01", "B", 2.5, "high"],
                             ["MT01", "A", 1, "low"], ["MT01", "B", 4, "low"]])
            with open(t, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["task_id", "reference_hours"])
                w.writerow(["MT01", 2])
            rows = ra.summarise(ra.load_ratings(r), ra.load_truth(t), ["MT01"], "anchor")
            pair = next(x for x in rows if x["measure"] == "pair_within_x1.5" and x["who"] == "A vs B")
            self.assertEqual(pair["value"], 0.0)
            gm = next(x for x in rows if x["measure"] == "within_x1.5_of_measured"
                      and x["who"] == "geometric mean of raters")
            self.assertEqual(gm["value"], 1.0)


class ProlificPipeline(unittest.TestCase):
    """Appendix G2: export, registered analysis, Table G2 and the screening comparison, on the synthetic demo."""

    def long_csv(self, d, *extra):
        out = Path(d) / "long.csv"
        r = run("pilot/prolific_to_long.py", out, *SOURCES, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return out, r.stdout

    def test_numbers_are_read_as_written(self):
        cases = {"8": 8.0, "2.5": 2.5, ".5": 0.5, "1,200": 1200.0, "12,000.5": 12000.5, "1,5": 1.5,
                 "about 6 hours": 6.0, "6h": 6.0, "0": 0.0}
        for text, value in cases.items():
            with self.subTest(text=text):
                self.assertEqual(ptl.number(text), value)
        for text in ("8-12", "8 to 12", "1 200", "3 hrs 30 min", "", "a day"):   # not one number: dropped as registered
            with self.subTest(text=text):
                self.assertIsNone(ptl.number(text))

    def test_report_lists_every_answer_that_is_not_a_plain_number(self):
        with tempfile.TemporaryDirectory() as d:
            out, stdout = self.long_csv(d, "--report")
            self.assertIn("5 answers were not a plain number", stdout)
            self.assertIn("'1,200' minutes -> 20 hours", stdout)
            self.assertIn("'8-12' hours -> kept as text: dropped by human_raters.py", stdout)
            with open(out, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len({(r["domain"], r["rater"]) for r in rows}), 26)

    def test_relabel_leaves_no_hash_to_recompute(self):
        with tempfile.TemporaryDirectory() as d:
            out, _ = self.long_csv(d, "--relabel")
            with open(out, encoding="utf-8") as fh:
                raters = {r["rater"] for r in csv.DictReader(fh)}
            self.assertEqual(raters, {f"R{i:03d}" for i in range(1, 27)})

    def test_table_g3_is_the_registered_scripts_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            out, _ = self.long_csv(d)
            printed = run("pilot/human_raters.py", out, "pilot/task-bank-v0.csv").stdout
            rows = {r["domain"]: r for r in table_g2.domain_rows(out, ROOT / "pilot" / "task-bank-v0.csv",
                                                                   ROOT / "pilot" / "results" / "model-ratings.csv")}
        blocks = re.split(r"\n== ", printed)[1:]
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            domain = block.split(":", 1)[0]
            r = rows[domain]
            with self.subTest(domain=domain):
                kept, excl, pairs = map(int, re.search(r"(\d+) raters kept, (\d+) excluded, (\d+) rater pairs", block).groups())
                self.assertEqual((kept, excl, pairs), (r["kept"], r["failed_attention"] + r["failed_competency"], r["pairs"]))
                self.assertEqual(re.search(r"pairs within x1.5: ([\d.]+)", block).group(1), f"{r['share']:.3f}")
                self.assertEqual(re.search(r"level: ([\d.]+)", block).group(1), f"{r['calibrated']:.3f}")
                self.assertEqual(re.search(r"log hours, \d+ complete raters: ([\d.]+)", block).group(1), f"{r['icc']:.3f}")
                self.assertEqual(re.search(r"test-retest within x1.5: ([\d.]+)", block).group(1), f"{r['retest']:.3f}")
                on_rung = sum(1 for line in block.splitlines()
                              if re.match(r"\w\w\d\d ", line) and line.split()[2] == line.split()[3])
                self.assertEqual(on_rung, r["on_rung"])

    def test_model_raters_on_the_twenty_tasks_give_the_papers_56_percent(self):
        models = ROOT / "pilot" / "results" / "model-ratings.csv"
        self.assertEqual(table_g2.model_share(models, "BK"), (28, 60))
        self.assertEqual(table_g2.model_share(models, "WT"), (39, 60))
        self.assertEqual(round(67 / 120 * 100), 56)

    def test_screen_compare(self):
        low, high = screen_compare.exact(11, 60)           # the bookkeeping screen of Appendix G2
        self.assertEqual((round(low * 100, 1), round(high * 100, 1)), (9.5, 30.4))
        self.assertAlmostEqual(screen_compare.tail(11, 60, low), 0.025, places=9)       # each end leaves 2.5%
        self.assertAlmostEqual(1 - screen_compare.tail(12, 60, high), 0.025, places=9)
        with tempfile.TemporaryDirectory() as d:
            out, _ = self.long_csv(d)
            r = run("pilot/screen_compare.py", out, "--reps", "200")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not registered", r.stdout)
        self.assertIn("== bookkeeping: 3 of 13 answered the question of the trade wrongly", r.stdout)
        self.assertIn("Week tasks (BK08, BK09, BK10)", r.stdout)


if __name__ == "__main__":
    unittest.main()
