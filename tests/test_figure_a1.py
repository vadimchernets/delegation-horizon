"""Tests for figures/figure_a1_calendar.py: Figure A1 drawn from predictions/predictions.csv.
The rows and dates are tested without matplotlib; drawing is tested where matplotlib is installed.
Standard library only: python3 -m unittest tests.test_figure_a1"""
import csv
import datetime as dt
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "figures"))
import figure_a1_calendar as a1  # noqa: E402

# The order of the rows in Figure A1 as published on 9 October 2026, read off the figure.
PUBLISHED_ORDER = ["F1", "F5", "F10", "F34", "F14", "F19", "F20", "F35", "F2", "F30", "F11", "F32", "F36", "F8", "F9",
                   "F13", "F15", "F16", "F21", "F28", "F28b", "F31", "F12", "F22", "F29", "F33", "F1b", "F7", "F6",
                   "F3", "F3b", "F4a", "F4b", "F27", "F17", "F17b", "F23", "F26", "F18", "F25", "F24"]
HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


def table():
    with (ROOT / "predictions" / "predictions.csv").open(newline="", encoding="utf-8") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


class Rows(unittest.TestCase):
    def test_the_order_of_the_published_figure(self):
        self.assertEqual([r["id"] for r in a1.rows()], PUBLISHED_ORDER)

    def test_every_check_and_final_date_is_read(self):
        for r in a1.rows():
            with self.subTest(prediction=r["id"]):
                self.assertIsInstance(r["final"], dt.date)
                self.assertLessEqual(r["start"], r["final"])
                self.assertIn(r["kind"], ("day", "bar", "on"))

    def test_the_kinds_of_check(self):
        kinds = {r["id"]: (r["kind"], r["label"]) for r in a1.rows()}
        self.assertEqual(kinds["F2"], ("day", ""))
        self.assertEqual(kinds["F1"], ("bar", "2027 data"))
        self.assertEqual(kinds["F10"], ("bar", "2027 report"))
        self.assertEqual(kinds["F29"], ("bar", "Taulbee report 2028"))
        self.assertEqual(kinds["F23"], ("on", "on publication of SOC 2028"))

    def test_the_two_commitments_come_from_the_table(self):
        rows = {r["id"]: r for r in a1.rows()}
        frozen = table()
        self.assertIn("frozen on Zenodo by 31 December 2026", frozen["F27"]["measure"])
        self.assertEqual(rows["F27"]["freeze"], dt.date(2026, 12, 31))
        self.assertEqual([k for k, r in rows.items() if r["freeze"]], ["F27"])
        set_b = {k for k, r in frozen.items() if r["set"] == "B"}
        self.assertEqual(len(set_b), 14)
        self.assertEqual({k for k, r in rows.items() if r["deadline"]}, set_b)
        for k in set_b:
            with self.subTest(prediction=k):
                self.assertIn("30 June 2027", frozen[k]["registration_deadline"])
                self.assertEqual(rows[k]["deadline"], dt.date(2027, 6, 30))

    def test_titles_and_probabilities_are_the_tables(self):
        frozen = table()
        for r in a1.rows():
            with self.subTest(prediction=r["id"]):
                self.assertEqual(r["p"], frozen[r["id"]]["probability"])
                if r["id"] not in a1.SHORT:
                    self.assertTrue(frozen[r["id"]]["prediction"].startswith(r["title"]))
                else:   # a shortened title must be the registered changelog's own words
                    log = (ROOT / "predictions" / "changelog-v1-v2.md").read_text(encoding="utf-8")
                    self.assertIn(r["title"].lower(), log.lower())

    def test_bar_labels_are_the_tables_words(self):
        for r in a1.rows():
            if r["kind"] == "bar":
                with self.subTest(prediction=r["id"]):
                    self.assertIn(r["label"], table()[r["id"]]["check_date"])


@unittest.skipUnless(HAS_MATPLOTLIB, "matplotlib is not installed; only the figure scripts need it")
class Drawing(unittest.TestCase):
    def test_draws_the_same_png_and_svg_every_time(self):
        digests = []
        with tempfile.TemporaryDirectory() as d:
            os.environ.setdefault("MPLCONFIGDIR", d)
            for run in ("a", "b"):
                out = str(Path(d) / run)
                a1.draw(out)
                digests.append([hashlib.sha256(Path(out + ext).read_bytes()).hexdigest() for ext in (".png", ".svg")])
                self.assertGreater(Path(out + ".png").stat().st_size, 100000)
        self.assertEqual(digests[0], digests[1])


class Listed(unittest.TestCase):
    def test_the_figures_readme_names_the_script(self):
        self.assertIn("figure_a1_calendar.py", (ROOT / "figures" / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
