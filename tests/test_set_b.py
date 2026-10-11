"""Tests for predictions/set_b.py: the frozen interval rules of Set B and the two intervals they are written on (the
power calculation of Section 11.2 is tools/power.py). Standard library only; run from the repository root:
python3 -m unittest tests.test_set_b"""
import csv
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "predictions" / "set_b.py"
TABLE = ROOT / "predictions" / "predictions.csv"
PY = sys.executable
sys.path.insert(0, str(ROOT / "predictions"))
import set_b  # noqa: E402

CAME, DID_NOT, UNRESOLVED = "came true", "did not", "unresolved"
Z95 = NormalDist().inv_cdf(0.975)
Z90 = NormalDist().inv_cdf(0.95)

# Breslow and Day (1980), Ille-et-Vilaine study of oesophageal cancer: alcohol 80 g/day or more against less, in six
# age strata. One tuple per stratum: (cases exposed, controls exposed, cases unexposed, controls unexposed).
# Totals 200 cases and 775 controls; crude odds ratio 96 * 666 / (104 * 109) = 5.64; Mantel-Haenszel 5.16.
BRESLOW_DAY = [("25-34", 1, 9, 0, 106), ("35-44", 4, 26, 5, 164), ("45-54", 25, 29, 21, 138),
               ("55-64", 42, 27, 34, 139), ("65-74", 19, 18, 36, 88), ("75+", 5, 0, 8, 31)]


def frozen():
    with open(TABLE, newline="", encoding="utf-8") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def run(*args):
    return subprocess.run([PY, str(SCRIPT)] + [str(a) for a in args], capture_output=True, text=True, cwd=ROOT,
                          timeout=60, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def write(folder, name, text):
    path = Path(folder) / name
    path.write_text(text, encoding="utf-8")
    return path


def spoken(x):
    """A threshold as the frozen table writes it: zero, minus 10, 0.75."""
    if x == 0:
        return "zero"
    return ("minus " if x < 0 else "") + format(abs(x), "g")


class Rules(unittest.TestCase):
    """Each rule's three outcomes (two for F12) on constructed intervals, with the bounds that sit on a threshold."""

    def v(self, pid, est, lo, hi):
        return set_b.judge(pid, est, lo, hi)[0]

    def test_f2(self):
        self.assertEqual(self.v("F2", -4, -7.5, -0.5), CAME)
        self.assertEqual(self.v("F2", -6, -9.99, -2), CAME)
        self.assertEqual(self.v("F2", -14, -17, -11), DID_NOT)
        self.assertEqual(self.v("F2", -8, -12, -4), UNRESOLVED)
        self.assertEqual(self.v("F2", -6, -10, -2), UNRESOLVED)       # lower exactly -10 is not above -10
        self.assertEqual(self.v("F2", -12, -14, -10), UNRESOLVED)     # upper exactly -10 is not below -10

    def test_f3_and_f3b(self):
        for pid in ("F3", "F3b"):
            with self.subTest(pid=pid):
                self.assertEqual(self.v(pid, 3, 0.2, 5.8), CAME)
                self.assertEqual(self.v(pid, -3, -5.8, -0.2), DID_NOT)
                self.assertEqual(self.v(pid, 1, -2.4, 4.4), UNRESOLVED)
                self.assertEqual(self.v(pid, 3, 0, 6), UNRESOLVED)    # lower exactly zero is not above zero
                self.assertEqual(self.v(pid, -3, -6, 0), UNRESOLVED)  # upper exactly zero is not below zero

    def test_f4a_and_f4b(self):
        for pid in ("F4a", "F4b"):
            with self.subTest(pid=pid):
                self.assertEqual(self.v(pid, 4, -1, 9.9), CAME)
                self.assertEqual(self.v(pid, 15, 10.1, 19.9), DID_NOT)
                self.assertEqual(self.v(pid, 8, 3, 13), UNRESOLVED)
                self.assertEqual(self.v(pid, 5, 0, 10), UNRESOLVED)   # upper exactly 10 is not below 10
                self.assertEqual(self.v(pid, 15, 10, 20), UNRESOLVED)  # lower exactly 10 is not above 10

    def test_f7(self):
        def f(day, week_up):
            return set_b.judge_f7(day, week_up)[0]
        within, wide, high, low = (1.0, 0.8, 1.25), (1.0, 0.6, 1.7), (2.0, 1.6, 2.5), (0.4, 0.3, 0.6)
        self.assertEqual(f(within, within), CAME)
        self.assertEqual(f(within, wide), UNRESOLVED)                 # equivalence at one level only
        self.assertEqual(f(wide, within), UNRESOLVED)
        self.assertEqual(f(wide, wide), UNRESOLVED)
        self.assertEqual(f(within, high), DID_NOT)                    # wholly outside at one level is enough
        self.assertEqual(f(low, within), DID_NOT)
        self.assertEqual(f(high, low), DID_NOT)
        self.assertEqual(f(wide, high), DID_NOT)
        self.assertEqual(f((1.0, 0.67, 1.5), (1.1, 0.67, 1.5)), CAME)  # the margin itself counts as within
        self.assertEqual(f((0.6, 0.5, 0.67), within), UNRESOLVED)     # touching 0.67 is not wholly outside
        self.assertEqual(f(within, (1.6, 1.5, 1.8)), UNRESOLVED)      # touching 1.5 is not wholly outside

    def test_f12_has_no_unresolved_interval(self):
        self.assertEqual(self.v("F12", 6, 1.5, 10.5), CAME)
        self.assertEqual(self.v("F12", 2, -2.5, 6.5), DID_NOT)        # "otherwise": across zero is did not
        self.assertEqual(self.v("F12", -5, -9, -1), DID_NOT)
        self.assertEqual(self.v("F12", 4, 0, 8), DID_NOT)             # lower exactly zero does not exclude zero

    def test_f26(self):
        self.assertEqual(self.v("F26", 1, -2.5, 4.5), CAME)
        self.assertEqual(self.v("F26", -2, -4.9, 0.9), CAME)
        self.assertEqual(self.v("F26", 0, -5, 5), CAME)               # the interval may touch plus or minus 5
        self.assertEqual(self.v("F26", 2.5, -0.5, 5.5), UNRESOLVED)   # estimate under 3, interval reaches 5.5
        self.assertEqual(self.v("F26", 4.5, 3.2, 5.8), DID_NOT)
        self.assertEqual(self.v("F26", -4.5, -5.8, -3.2), DID_NOT)
        self.assertEqual(self.v("F26", 3, 1.5, 4.5), UNRESOLVED)      # a gap of exactly 3 is not less than 3
        self.assertEqual(self.v("F26", 4, 3, 5), UNRESOLVED)          # lower exactly 3 is not beyond 3
        self.assertEqual(self.v("F26", -3.5, -6, -1), UNRESOLVED)

    def test_f34(self):
        self.assertEqual(self.v("F34", 0.86, 0.79, 0.91), CAME)
        self.assertEqual(self.v("F34", 0.82, 0.75, 0.90), CAME)       # "0.75 or above" includes 0.75
        self.assertEqual(self.v("F34", 0.62, 0.48, 0.74), DID_NOT)
        self.assertEqual(self.v("F34", 0.80, 0.70, 0.88), UNRESOLVED)
        self.assertEqual(self.v("F34", 0.70, 0.60, 0.75), UNRESOLVED)  # upper exactly 0.75 is not below 0.75

    def test_ids_are_matched_without_case(self):
        self.assertEqual(self.v("f3B", 3, 0.2, 5.8), CAME)

    def test_impossible_intervals_are_refused(self):
        bad = [("F2", -4, -1, -7),                 # lower above upper
               ("F2", 5, -7, -1),                  # estimate outside its interval
               ("F2", float("nan"), -7, -1),
               ("F3", 0, -120, 5),                 # a difference of shares beyond 100 points
               ("F34", 0.9, 0.8, 1.2),             # an ICC above 1
               ("F99", 0, -1, 1), ("F14", 0, -1, 1), ("F5", 0, -1, 1),
               ("F7", 1.0, 0.8, 1.2)]              # F7 needs two levels
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                set_b.judge(*args)
        with self.assertRaises(ValueError):
            set_b.judge_f7((1.0, 0.0, 1.2), (1.0, 0.8, 1.2))   # an odds ratio interval must lie above zero


class FrozenText(unittest.TestCase):
    """Only the numbers are in set_b.py; the words come from the frozen table, and each number must be the one
    the frozen words state, in the column it governs."""

    @classmethod
    def setUpClass(cls):
        cls.t = frozen()

    def test_every_threshold_is_in_the_frozen_words(self):
        R = set_b.RULES

        def level(pid):
            return format(R[pid]["level"] * 100, "g") + "% interval"
        came, did, unres = "came_true_if", "did_not_come_true_if", "unresolved_if"
        expected = []
        for pid in ("F2", "F3", "F3b"):
            expected += [(pid, came, "lower bound of the " + level(pid)),
                         (pid, came, "above " + spoken(R[pid]["cut"])),
                         (pid, did, "upper bound of the " + level(pid)),
                         (pid, did, "below " + spoken(R[pid]["cut"]))]
        expected += [("F2", came, "above " + spoken(R["F2"]["cut"]) + " points"),
                     ("F2", did, "below " + spoken(R["F2"]["cut"]) + " points")]
        for pid in ("F4a", "F4b"):
            expected += [(pid, came, "upper bound of the " + level(pid)),
                         (pid, came, "below " + spoken(R[pid]["cut"]) + " points"),
                         (pid, did, "lower bound"),
                         (pid, did, "above " + spoken(R[pid]["cut"]) + " points")]
        low, high = format(R["F7"]["low"], "g"), format(R["F7"]["high"], "g")
        expected += [("F7", came, level("F7")),
                     ("F7", came, "within " + low + " to " + high),
                     ("F7", came, "at Day and at Week and above"),
                     ("F7", did, level("F7")),
                     ("F7", did, "wholly outside " + low + " to " + high),
                     ("F7", did, "at Day or at Week and above"),
                     ("F7", unres, "one level only")]
        expected += [("F12", came, level("F12") + " excluding " + spoken(R["F12"]["cut"])),
                     ("F12", came, "is higher"),
                     ("F12", did, "Otherwise")]
        gap, margin = format(R["F26"]["gap"], "g"), format(R["F26"]["margin"], "g")
        expected += [("F26", came, "less than " + gap + " points"),
                     ("F26", came, level("F26") + " inside plus or minus " + margin + " points"),
                     ("F26", did, level("F26")),
                     ("F26", did, "wholly beyond " + gap + " points in either direction")]
        expected += [("F34", came, "lower bound of the " + level("F34")),
                     ("F34", came, format(R["F34"]["cut"], "g") + " or above"),
                     ("F34", did, "upper bound is below " + format(R["F34"]["cut"], "g"))]
        for pid, column, phrase in expected:
            with self.subTest(pid=pid, column=column, phrase=phrase):
                self.assertIn(phrase, self.t[pid][column])
        self.assertEqual({pid for pid, _, _ in expected}, set(R))

    def test_three_outcomes_where_the_text_has_three(self):
        for pid, rule in set_b.RULES.items():
            with self.subTest(pid=pid):
                text = self.t[pid]["unresolved_if"]
                if pid == "F12":
                    self.assertNotIn("interval", text)       # an interval can never leave F12 unresolved
                elif pid == "F7":
                    self.assertIn("Any other combination", text)
                else:
                    self.assertIn("an interval that meets neither rule", text)

    def test_set_b_is_the_fourteen_of_section_11_2(self):
        in_b = {pid for pid, r in self.t.items() if r["set"] == "B"}
        self.assertEqual(in_b, {"F2", "F3", "F3b", "F4a", "F4b", "F7", "F12", "F14", "F18", "F19", "F20",
                                "F26", "F34", "F35"})
        self.assertEqual(set(set_b.RULES), {"F2", "F3", "F3b", "F4a", "F4b", "F7", "F12", "F26", "F34"})
        self.assertEqual(set(set_b.RULES) | set(set_b.NOT_INTERVAL), in_b)
        for pid in set_b.RULES:
            self.assertIn("interval", self.t[pid]["came_true_if"], pid)
        for pid in set_b.NOT_INTERVAL:
            self.assertNotIn("interval", self.t[pid]["came_true_if"], pid)

    def test_rule_texts_are_read_not_copied(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for pid in set_b.RULES:
            for column in ("came_true_if", "did_not_come_true_if", "unresolved_if"):
                with self.subTest(pid=pid, column=column):
                    self.assertNotIn(self.t[pid][column], source)

    def test_verdict_prints_the_frozen_texts_and_checks_the_table(self):
        r = run("verdict", "--id", "F26", "--estimate", "2.5", "--lower", "-0.5", "--upper", "5.5")
        self.assertEqual(r.returncode, 0, r.stderr)
        for column in ("came_true_if", "did_not_come_true_if", "unresolved_if"):
            self.assertIn(self.t["F26"][column], r.stdout)
        self.assertIn("verdict: unresolved", r.stdout)
        self.assertIn("10.17605/OSF.IO/VW6P9", r.stdout)
        self.assertNotIn("WARNING", r.stdout)

    def test_a_changed_table_is_flagged(self):
        text = TABLE.read_text(encoding="utf-8").replace("lies above minus 10 points", "lies above minus 5 points")
        with tempfile.TemporaryDirectory() as d:
            changed = write(d, "predictions.csv", text)
            r = run("verdict", "--id", "F2", "--estimate", "-4", "--lower", "-7.5", "--upper", "-0.5",
                    "--predictions", changed)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WARNING", r.stdout)


class Newcombe(unittest.TestCase):
    def test_worked_example(self):
        # Newcombe (1998), Statistics in Medicine 17, 873-890, example (a), method 10: 56/70 against 48/80.
        d, lo, hi = set_b.newcombe(56, 70, 48, 80)
        self.assertAlmostEqual(d, 0.2000, places=4)
        self.assertAlmostEqual(lo, 0.0524, places=4)
        self.assertAlmostEqual(hi, 0.3339, places=4)

    def test_extremes_by_hand(self):
        # The Wilson upper bound of 0 of n is z^2 / (n + z^2), and its lower bound of n of n is n / (n + z^2).
        u = Z95 ** 2 / (10 + Z95 ** 2)
        d, lo, hi = set_b.newcombe(0, 10, 0, 10)
        self.assertEqual(d, 0)
        self.assertAlmostEqual(lo, -u, places=12)
        self.assertAlmostEqual(hi, u, places=12)
        d, lo, hi = set_b.newcombe(10, 10, 0, 10)
        self.assertEqual(d, 1)
        self.assertAlmostEqual(lo, 1 - math.sqrt(2) * u, places=12)   # 0.6075
        self.assertAlmostEqual(hi, 1.0, places=12)

    def test_swapping_the_groups_mirrors_the_interval(self):
        d, lo, hi = set_b.newcombe(48, 80, 56, 70)
        self.assertAlmostEqual(d, -0.2000, places=4)
        self.assertAlmostEqual(lo, -0.3339, places=4)
        self.assertAlmostEqual(hi, -0.0524, places=4)

    def test_a_lower_level_gives_a_narrower_interval(self):
        _, lo95, hi95 = set_b.newcombe(56, 70, 48, 80, 0.95)
        _, lo90, hi90 = set_b.newcombe(56, 70, 48, 80, 0.90)
        self.assertTrue(lo95 < lo90 < 0.2 < hi90 < hi95)

    def test_bad_counts(self):
        for args in ((71, 70, 48, 80), (5, 0, 4, 10), (-1, 70, 48, 80), (5, 10, 4, 10, 1.5)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                set_b.newcombe(*args)


class MantelHaenszel(unittest.TestCase):
    def test_one_stratum_is_woolf(self):
        # One stratum: the estimate is ad/bc and the Robins-Breslow-Greenland variance is Woolf's 1/a+1/b+1/c+1/d.
        est, lo, hi = set_b.mantel_haenszel([(20, 10, 10, 20)], conf=0.90)
        se = math.sqrt(1 / 20 + 1 / 10 + 1 / 10 + 1 / 20)
        self.assertAlmostEqual(est, 4.0)
        self.assertAlmostEqual(lo, math.exp(math.log(4) - Z90 * se))
        self.assertAlmostEqual(hi, math.exp(math.log(4) + Z90 * se))

    def test_two_strata_by_hand(self):
        # Stratum 1: a=4 b=2 c=2 d=4 (n=12); stratum 2: a=6 b=4 c=4 d=6 (n=20).
        # R = ad/n: 16/12 + 36/20 = 47/15; S = bc/n: 4/12 + 16/20 = 17/15; estimate 47/17.
        # P = (a+d)/n: 2/3 and 3/5; Q = (b+c)/n: 1/3 and 2/5.
        # sum PR = 8/9 + 27/25 = 443/225; sum (PS + QR) = 2/9 + 4/9 + 12/25 + 18/25 = 28/15;
        # sum QS = 1/9 + 8/25 = 97/225.
        # var log = (443/225) / (2 (47/15)^2) + (28/15) / (2 (47/15)(17/15)) + (97/225) / (2 (17/15)^2)
        #         = 443/4418 + 210/799 + 97/578 = 0.53092
        var = 443 / 4418 + 210 / 799 + 97 / 578
        for conf, z in ((0.90, Z90), (0.95, Z95)):
            with self.subTest(conf=conf):
                est, lo, hi = set_b.mantel_haenszel([(4, 2, 2, 4), (6, 4, 4, 6)], conf=conf)
                self.assertAlmostEqual(est, 47 / 17)
                self.assertAlmostEqual(lo, 47 / 17 * math.exp(-z * math.sqrt(var)))
                self.assertAlmostEqual(hi, 47 / 17 * math.exp(z * math.sqrt(var)))

    def test_breslow_day_oesophageal_cancer(self):
        # The textbook Mantel-Haenszel estimate 5.16; its Robins-Breslow-Greenland 95% interval is 3.56 to 7.47.
        est, lo, hi = set_b.mantel_haenszel([t[1:] for t in BRESLOW_DAY], conf=0.95)
        self.assertAlmostEqual(est, 5.1576, places=4)
        self.assertAlmostEqual(lo, 3.5621, places=4)
        self.assertAlmostEqual(hi, 7.4677, places=4)

    def test_undefined_estimate_is_refused(self):
        with self.assertRaises(ValueError):
            set_b.mantel_haenszel([(5, 0, 3, 7)])       # bc = 0 in every stratum: infinite odds ratio
        with self.assertRaises(ValueError):
            set_b.mantel_haenszel([(5, -1, 3, 7)])


class CommandLine(unittest.TestCase):
    def assertMessage(self, r, word):
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr + r.stdout)
        self.assertIn(word, r.stderr)

    def test_help(self):
        for args in ([], ["verdict"], ["diff"], ["or"]):
            with self.subTest(args=args):
                r = run(*(args + ["--help"]))
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("usage", r.stdout.lower())
        self.assertIn("Usage:", run("--help").stdout)
        self.assertMessage(run(), "usage")

    def test_verdict_from_values(self):
        r = run("verdict", "--id", "F2", "--estimate", "-4.2", "--lower", "-7.5", "--upper", "-0.9")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("verdict: came true", r.stdout)
        r = run("verdict", "--id", "F7", "--day", "1.02", "0.84", "1.24", "--week-up", "0.97", "0.61", "1.55")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("verdict: unresolved", r.stdout)

    def test_verdict_from_a_csv(self):
        rows = ("id,estimate,lower,upper,level\nF34,0.62,0.48,0.74,\nF7,1.02,0.84,1.24,day\n"
                "F12,2.0,-2.5,6.5,\nF7,0.97,0.61,1.55,week_up\nF2,-4.2,-7.5,-0.9,\n")
        with tempfile.TemporaryDirectory() as d:
            r = run("verdict", write(d, "estimates.csv", rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        verdicts = re.findall(r"verdict: (came true|did not|unresolved)", out)
        self.assertEqual(verdicts, [CAME, UNRESOLVED, DID_NOT, DID_NOT])    # F2, F7, F12, F34: the table's order
        self.assertLess(out.index("F2:"), out.index("F7 at Day"))
        self.assertLess(out.index("F12:"), out.index("F34:"))
        self.assertIn("came true: 1, did not: 2, unresolved: 1", out)

    def test_diff_applies_a_rule(self):
        r = run("diff", 56, 70, 48, 80, "--id", "F3")
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ("+20.00", "+5.24", "+33.39", "95%", "verdict: came true"):
            self.assertIn(word, r.stdout)
        r = run("diff", 56, 70, 48, 80)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("verdict", r.stdout)

    def test_or_from_a_csv(self):
        lines = ["stratum,group,passed,n"]
        for name, a, b, c, d in BRESLOW_DAY:
            lines += [f"{name},1,{a},{a + b}", f"{name},0,{c},{c + d}"]
        with tempfile.TemporaryDirectory() as d:
            r = run("or", write(d, "strata.csv", "\n".join(lines) + "\n"), "--conf", "0.95")
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ("5.158", "3.562", "7.468"):
            self.assertIn(word, r.stdout)

    def test_or_applies_f7(self):
        narrow = ["{lv},high,it,300,500", "{lv},high,other,290,500", "{lv},low,it,200,400", "{lv},low,other,205,400"]
        small = ["{lv},high,it,30,50", "{lv},high,other,28,50", "{lv},low,it,20,40", "{lv},low,other,21,40"]
        for week, verdict in ((narrow, CAME), (small, UNRESOLVED)):
            rows = ["level,stratum,group,passed,n"] + [x.format(lv="day") for x in narrow] + \
                   [x.format(lv="week_up") for x in week]
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as d:
                r = run("or", write(d, "f7.csv", "\n".join(rows) + "\n"), "--exposed", "it", "--id", "F7")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("90%", r.stdout)
                self.assertIn("verdict: " + verdict, r.stdout)

    def test_bad_input_gives_a_message_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            swapped = write(d, "swapped.csv", "id,estimate,lower,upper\nF3,1,-2,4\nF2,-4,-1,-7\n")
            one_f7 = write(d, "one.csv", "id,estimate,lower,upper,level\nF7,1.0,0.8,1.2,day\n")
            twice = write(d, "twice.csv", "id,estimate,lower,upper\nF3,1,-2,4\nF3,1,-2,4\n")
            columns = write(d, "columns.csv", "id;estimate;lower;upper\nF3;1;-2;4\n")
            three = write(d, "three.csv", "stratum,group,passed,n\ns,1,3,10\ns,0,4,10\ns,2,5,10\n")
            cases = [
                (["verdict", "--id", "F99", "--estimate", "1", "--lower", "0", "--upper", "2"], "F99"),
                (["verdict", "--id", "F5", "--estimate", "1", "--lower", "0", "--upper", "2"], "Set A"),
                (["verdict", "--id", "F14", "--estimate", "1", "--lower", "0", "--upper", "2"], "interval rule"),
                (["verdict", "--id", "F2", "--estimate", "-4", "--lower", "-1", "--upper", "-7"], "lower bound"),
                (["verdict", "--id", "F2", "--estimate", "nan", "--lower", "-7", "--upper", "-1"], "finite"),
                (["verdict", "--id", "F2", "--estimate", "abc", "--lower", "-7", "--upper", "-1"], "invalid float"),
                (["verdict", "--id", "F2", "--estimate", "-4"], "--lower"),
                (["verdict", "--id", "F7", "--day", "1", "0.8", "1.2"], "--week-up"),
                (["verdict"], "CSV"),
                (["verdict", Path(d) / "no-such-file.csv"], "no-such-file.csv"),
                (["verdict", swapped], "line 3"),
                (["verdict", one_f7], "two rows"),
                (["verdict", twice], "twice"),
                (["verdict", columns], "missing column"),
                (["diff", 71, 70, 48, 80], "71 of 70"),
                (["diff", 56, 70, 48, 80, "--id", "F7"], "or subcommand"),
                (["diff", 56, 70, 48, 80, "--id", "F2", "--conf", "0.90"], "95%"),
                (["or", three, "--id", "F7"], "two values"),
            ]
            for args, word in cases:
                with self.subTest(args=args):
                    self.assertMessage(run(*args), word)


FORBIDDEN = "[" + chr(0x400) + "-" + chr(0x4FF) + chr(0x2013) + chr(0x2014) + "]"   # Cyrillic, en dash, em dash


class HouseRules(unittest.TestCase):
    def test_docstring(self):
        doc = set_b.__doc__
        self.assertTrue(doc.splitlines()[0].startswith("set_b.py: "))
        for word in ("Teaches:", "Limits:", "Usage:", "Licence: MIT"):
            self.assertIn(word, doc)

    def test_english_and_no_long_dashes(self):
        for path in (SCRIPT, Path(__file__)):
            with self.subTest(file=path.name):
                self.assertIsNone(re.search(FORBIDDEN, path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
