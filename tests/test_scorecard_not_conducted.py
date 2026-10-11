"""The status "not conducted" on the scorecard (Sections 11.2 and 11.4, Appendix D): a Set B prediction whose
protocol is not registered by 30 June 2027 is listed on every scorecard, left out of the first Brier score and
scored as wrong in the second. Standard library only: python3 -m unittest tests.test_scorecard_not_conducted"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / "predictions"))
import skill  # noqa: E402

DEADLINE = "Protocol registered by 30 June 2027, otherwise recorded as not conducted"


def run(*args):
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=120)


class ScoreNotConducted(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "p.csv").write_text(
            "id,probability,set,registration_deadline,final_date\n"
            "A,0.4,A,,31 December 2028\n"
            f"B,0.7,B,{DEADLINE},8 October 2028\n"
            f"C,0.2,B,{DEADLINE},8 October 2029\n", encoding="utf-8")

    def score(self, outcomes, *extra):
        (self.tmp / "o.csv").write_text("id,status,evidence,scored_on\n" + outcomes, encoding="utf-8")
        return run("predictions/score.py", self.tmp / "o.csv", "--predictions", self.tmp / "p.csv", *extra)

    def test_two_brier_scores_and_the_list(self):
        r = self.score("A,came_true,,2027-10-09\nB,not_conducted,,2027-10-09\nC,did_not,,2027-10-09\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Brier score over 2 resolved: 0.200", r.stdout)               # (0.36 + 0.04) / 2
        self.assertIn("not conducted, a failure of the testing programme: B", r.stdout)
        self.assertIn("with every prediction not conducted scored as wrong: Brier score over 3: 0.297", r.stdout)
        self.assertIn("not conducted: 1", r.stdout)
        self.assertNotIn("unresolved or not yet due: B", r.stdout)

    def test_set_a_cannot_be_not_conducted(self):
        r = self.score("A,not_conducted,,2027-10-09\nB,did_not,,2027-10-09\nC,did_not,,2027-10-09\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("A: not_conducted applies to Set B only", r.stdout + r.stderr)

    def test_not_conducted_only_after_the_deadline(self):
        r = self.score("A,came_true,,2027-05-01\nB,not_conducted,,2027-05-01\nC,did_not,,2027-05-01\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("B: not conducted only after 30 June 2027", r.stdout + r.stderr)
        r = self.score("A,came_true,,\nB,not_conducted,,\nC,did_not,,\n", "--as-of", "2027-07-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.score("A,came_true,,\nB,not_conducted,,\nC,did_not,,\n", "--as-of", "2027-06-30")
        self.assertNotEqual(r.returncode, 0)

    def test_table_without_sets_refuses_not_conducted(self):
        (self.tmp / "p.csv").write_text("id,probability\nA,0.4\nB,0.7\n", encoding="utf-8")
        r = self.score("A,came_true,,2027-10-09\nB,not_conducted,,2027-10-09\n")
        self.assertNotEqual(r.returncode, 0)

    def test_registered_table_still_scores_the_template(self):
        r = run("predictions/score.py", "predictions/outcomes-template.csv")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not yet due: 41", r.stdout)
        self.assertIn("not conducted: 0", r.stdout)


class SkillNotConducted(unittest.TestCase):
    PREDS = [
        {"id": "A", "probability": "0.4", "final_date": "31 December 2028", "set": "A", "family": "A"},
        {"id": "B", "probability": "0.7", "final_date": "8 October 2028", "set": "B", "family": "B",
         "registration_deadline": DEADLINE},
        {"id": "C", "probability": "0.2", "final_date": "8 October 2029", "set": "B", "family": "C",
         "registration_deadline": DEADLINE},
    ]

    def test_worst_bound_and_second_score_count_it_as_wrong(self):
        out = skill.scores(self.PREDS, {"A": "came_true", "B": "not_conducted", "C": "did_not"}, dt.date(2027, 10, 9))
        self.assertEqual(out["resolved"], 2)
        self.assertEqual(out["not_conducted"], 1)
        self.assertAlmostEqual(out["brier"], (0.36 + 0.04) / 2)
        self.assertAlmostEqual(out["brier_not_conducted_as_wrong"], (0.36 + 0.04 + 0.49) / 3)
        self.assertAlmostEqual(out["brier_worst_bound"], (0.36 + 0.04 + 0.49) / 3)

    def test_low_probability_not_conducted_is_wrong_the_other_way(self):
        out = skill.scores(self.PREDS, {"A": "came_true", "B": "did_not", "C": "not_conducted"}, dt.date(2027, 10, 9))
        self.assertAlmostEqual(out["brier_not_conducted_as_wrong"], (0.36 + 0.49 + 0.64) / 3)   # C: p 0.2, wrong = 1

    def test_set_a_or_early_not_conducted_is_refused(self):
        with self.assertRaises(ValueError):
            skill.scores(self.PREDS, {"A": "not_conducted"}, dt.date(2027, 10, 9))
        with self.assertRaises(ValueError):
            skill.scores(self.PREDS, {"B": "not_conducted"}, dt.date(2027, 6, 30))

    def test_unknown_status_and_missing_prediction_are_refused(self):
        tmp = Path(tempfile.mkdtemp())
        out = tmp / "o.csv"
        out.write_text("id,status,evidence,scored_on\nF1,maybe,,\n", encoding="utf-8")
        r = run("predictions/skill.py", out, "--today", "2027-10-09")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("F1: status must be", r.stdout + r.stderr)
        out.write_text("id,status,evidence,scored_on\nF1,came_true,,\n", encoding="utf-8")
        r = run("predictions/skill.py", out, "--today", "2027-10-09")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("every frozen prediction must appear", r.stdout + r.stderr)

    def test_template_runs(self):
        r = run("predictions/skill.py", "predictions/outcomes-template.csv", "--today", "2027-10-09")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not_conducted: 0", r.stdout)


if __name__ == "__main__":
    unittest.main()
