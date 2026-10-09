"""Tests for the frozen predictions table and the extra scores (stdlib unittest)."""
import csv
import datetime as dt
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "predictions"))
import skill  # noqa: E402

TABLE = os.path.join(ROOT, "predictions", "predictions.csv")
REQUIRED = ["id", "prediction", "measure", "baseline", "check_date", "final_date", "probability",
            "came_true_if", "did_not_come_true_if", "unresolved_if", "fallback_source",
            "nearest_prior_or_counter_forecast", "resolved_by"]


def rows():
    with open(TABLE, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class TableTest(unittest.TestCase):
    def test_columns_and_rules(self):
        rs = rows()
        self.assertGreaterEqual(len(rs), 29)
        for r in rs:
            for c in REQUIRED:
                self.assertIn(c, r)
            for c in ("came_true_if", "did_not_come_true_if", "unresolved_if"):
                self.assertTrue(r[c].strip(), f"{r['id']}: empty {c}")
            p = float(r["probability"])
            self.assertTrue(0.0 < p < 1.0, r["id"])

    def test_unique_ids_and_outcomes(self):
        rs = rows()
        self.assertEqual(len({r["id"] for r in rs}), len(rs))
        self.assertEqual(len({r["came_true_if"] for r in rs}), len(rs), "two predictions share an outcome")

    def test_ascii_only_no_long_dash(self):
        with open(TABLE, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIsNone(re.search("[\\u0400-\\u04ff]", text))
        self.assertNotIn("\\u2014", text)


class SkillTest(unittest.TestCase):
    def test_toy_outcomes(self):
        preds = [
            {"id": "A", "probability": "0.8", "final_date": "31 December 2027", "set": "A", "family": "x",
             "models_geomean_odds": "0.6", "market_price": ""},
            {"id": "B", "probability": "0.3", "final_date": "31 December 2027", "set": "B", "family": "x",
             "models_geomean_odds": "0.5", "market_price": "0.4"},
            {"id": "C", "probability": "0.7", "final_date": "31 December 2027", "set": "A", "family": "C",
             "models_geomean_odds": "", "market_price": ""},
        ]
        out = skill.scores(preds, {"A": "came_true", "B": "did_not", "C": "unresolved"}, dt.date(2028, 1, 1))
        self.assertEqual(out["resolved"], 2)
        self.assertAlmostEqual(out["brier"], (0.04 + 0.09) / 2)
        self.assertAlmostEqual(out["brier_worst_bound"], (0.04 + 0.09 + 0.49) / 3)
        self.assertAlmostEqual(out["skill"]["flat_0.5"], 1 - 0.065 / 0.25)
        self.assertIn("models", out["skill"])
        self.assertIn("market", out["skill"])

    def test_unresolved_before_final_date_not_in_worst_bound(self):
        preds = [{"id": "A", "probability": "0.7", "final_date": "31 December 2030"}]
        out = skill.scores(preds, {"A": "unresolved"}, dt.date(2028, 1, 1))
        self.assertIsNone(out["brier_worst_bound"])


if __name__ == "__main__":
    unittest.main()
