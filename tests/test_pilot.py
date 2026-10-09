"""Tests for the desk pre-pilot scripts (pilot/). Standard library only: python3 -m unittest"""
import csv
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pilot"))
import rater_agreement as ra  # noqa: E402
import simulate_rules as sim  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
