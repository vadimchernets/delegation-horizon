"""Tests for tools/gate_leak.py and tools/process_study.py, and for the kits of Sections 6.2, 6.5 and 10.5
(kits/trade-screen.md, kits/checking-process.md, kits/process-vs-experience-study.md). The kit tests follow
the content: example log lines must be valid for horizon.py, a quoted command must print what the kit
quotes, and a kit that names either tool names only files that exist.
Standard library only, no network. Run from the repository root: python3 -m unittest -v"""
import ast
import csv
import json
import math
import random
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
KITS = ROOT / "kits"
PY = sys.executable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS))
import horizon  # noqa: E402
import gate_leak  # noqa: E402
import process_study  # noqa: E402

GATE = TOOLS / "gate_leak.py"
STUDY = TOOLS / "process_study.py"
NEW_KITS = ["checking-process.md", "process-vs-experience-study.md", "trade-screen.md"]


def kits_with_these_tools():
    """The kits that go with these tools: those of NEW_KITS that name tools/gate_leak.py or tools/process_study.py."""
    return [k for k in NEW_KITS if (KITS / k).exists() and
            re.search(r"tools/(gate_leak|process_study)\.py", (KITS / k).read_text(encoding="utf-8"))]

CELLS = [("absent", "one_agent"), ("absent", "process"), ("present", "one_agent"), ("present", "process")]
ERR_HEAD = ["participant", "experience", "way", "rung", "kind", "caught"]
PIECE_HEAD = ["participant", "experience", "way", "rung", "verified"]
ANSWER_HEAD = ["participant", "group", "admitted_by", "answer_correct"]
# designed shares of planted errors caught, in the order of CELLS
WRONG = dict(zip(CELLS, (0.50, 0.70, 0.80, 0.85)))   # process +20, experience +30, interaction -15, gap 67%
OMIT = dict(zip(CELLS, (0.20, 0.40, 0.55, 0.65)))    # process +20, experience +35, interaction -10, gap 57%
FLAT = dict(zip(CELLS, (0.50, 0.70, 0.52, 0.80)))    # experience barely matters under one agent (+2)


def run(*args):
    return subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True, cwd=ROOT, timeout=300)


def write_csv(folder, name, header, rows):
    path = Path(folder) / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def binomial_tail(k, n, p, upper):
    """P(X >= k) if upper, else P(X <= k), summed with math.comb: independent of the tool's own code."""
    ks = range(k, n + 1) if upper else range(0, k + 1)
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in ks)


def planted(designs, people=20, per_person=5, seed=5):
    """One row per planted error. designs: {rung: {kind: {cell: share}}}. Every cell's share is exact,
    and the catches are spread unevenly over its people, so the bootstrap has something to resample."""
    rng = random.Random(seed)
    rows = []
    for exp, way in CELLS:
        ids = [f"{exp[:2]}-{way[:3]}-{i:02d}" for i in range(people)]
        for rung, kinds in designs.items():
            for kind, shares in kinds.items():
                total = people * per_person
                hits = round(shares[(exp, way)] * total)
                outcomes = [1] * hits + [0] * (total - hits)
                rng.shuffle(outcomes)
                for i, pid in enumerate(ids):
                    rows += [[pid, exp, way, rung, kind, o] for o in outcomes[i * per_person:(i + 1) * per_person]]
    return rows


def pieces_rows(shares, people=20, per_person=3, rung="Day", seed=9):
    """One row per piece, for the same people as planted(); shares: {cell: share verified}."""
    rng = random.Random(seed)
    rows = []
    for exp, way in CELLS:
        total = people * per_person
        hits = round(shares[(exp, way)] * total)
        outcomes = [1] * hits + [0] * (total - hits)
        rng.shuffle(outcomes)
        for i in range(people):
            pid = f"{exp[:2]}-{way[:3]}-{i:02d}"
            rows += [[pid, exp, way, rung, o] for o in outcomes[i * per_person:(i + 1) * per_person]]
    return rows


def records(rows):
    """Rows of planted() in the form process_study.analyse() takes."""
    return [{"participant": r[0], "cell": (r[1], r[2]), "rung": r[3], "kind": r[4], "outcome": r[5]} for r in rows]


def block(out, title):
    """One block of process_study's output: from its title line to the next blank line."""
    lines = out.splitlines()
    start = lines.index(f"== {title} ==")
    end = next((i for i in range(start, len(lines)) if not lines[i].strip()), len(lines))
    return "\n".join(lines[start:end])


def one_line_error(test, r, *needles):
    test.assertNotEqual(r.returncode, 0, r.stdout)
    test.assertNotIn("Traceback", r.stderr)
    test.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
    for needle in needles:
        test.assertIn(needle, r.stderr)


class ClopperPearson(unittest.TestCase):
    def test_prolific_bookkeeping_sample(self):
        # Appendix G2: 11 of the 60 people the filters admitted answered the question of the trade wrongly
        lo, hi = gate_leak.clopper_pearson(11, 60)
        self.assertEqual((round(lo * 100, 1), round(hi * 100, 1)), (9.5, 30.4))
        # the defining property: each end leaves 2.5% in the exact binomial tail beyond it
        self.assertAlmostEqual(binomial_tail(11, 60, lo, upper=True), 0.025, places=9)
        self.assertAlmostEqual(binomial_tail(11, 60, hi, upper=False), 0.025, places=9)

    def test_eight_of_ten_as_in_section_5_8(self):
        lo, hi = gate_leak.clopper_pearson(8, 10)
        self.assertEqual((round(lo * 100, 1), round(hi * 100, 1)), (44.4, 97.5))

    def test_closed_forms_at_the_edges(self):
        lo, hi = gate_leak.clopper_pearson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.025 ** 0.1, places=9)
        lo, hi = gate_leak.clopper_pearson(10, 10)
        self.assertAlmostEqual(lo, 0.025 ** 0.1, places=9)
        self.assertEqual(hi, 1.0)
        # three of three: the one-sided 95% bound of about 37% (Section 5.8) is the lower end at 90%
        self.assertAlmostEqual(gate_leak.clopper_pearson(3, 3, level=0.90)[0], 0.05 ** (1 / 3), places=9)

    def test_impossible_counts_are_refused(self):
        for k, n in ((11, 10), (-1, 10), (0, 0)):
            with self.subTest(k=k, n=n), self.assertRaises(ValueError):
                gate_leak.clopper_pearson(k, n)

    def test_admission_factor(self):
        self.assertAlmostEqual(gate_leak.admission_factor(11 / 60), 60 / 49)
        self.assertEqual(gate_leak.admission_factor(0.0), 1.0)
        self.assertTrue(math.isinf(gate_leak.admission_factor(1.0)))


class Wilson(unittest.TestCase):
    def test_textbook_case(self):
        lo, hi = process_study.wilson(81, 263)
        self.assertAlmostEqual(lo, 0.2553, places=4)
        self.assertAlmostEqual(hi, 0.3662, places=4)

    def test_ends_solve_the_score_equation(self):
        # Wilson's interval holds the p with (k/n - p)^2 <= z^2 p (1 - p) / n; its ends meet it with equality
        z = 1.959963984540054
        for k, n in ((81, 263), (3, 7), (0, 12), (12, 12)):
            for p in process_study.wilson(k, n):
                with self.subTest(k=k, n=n, p=p):
                    self.assertAlmostEqual((k / n - p) ** 2, z * z * p * (1 - p) / n, places=12)
                    self.assertTrue(0.0 <= p <= 1.0)


class GateLeakCli(unittest.TestCase):
    def test_counts(self):
        r = run(GATE, "--admitted", 60, "--failed", 11, "--label", "Prolific occupation filter")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gate: Prolific occupation filter", r.stdout)
        self.assertIn("admitted by the label: 60", r.stdout)
        self.assertIn("failed the check of the trade: 11", r.stdout)
        self.assertIn("share failing: 18.3% (exact 95% interval 9.5% to 30.4%, Clopper-Pearson)", r.stdout)
        self.assertIn("admission factor: 1.22 (1.11 to 1.44)", r.stdout)

    def test_csv_gives_one_block_per_group(self):
        rows = [[f"B{i:02d}", "bookkeeping", "Prolific occupation filter", 0 if i < 11 else 1] for i in range(60)]
        rows += [[f"D{i:03d}", "developers", "reported Node.js", 1 if i < 55 else 0] for i in range(206)]
        with tempfile.TemporaryDirectory() as d:
            r = run(GATE, write_csv(d, "answers.csv", ANSWER_HEAD, rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        blocks = r.stdout.strip().split("\n\n")
        self.assertEqual(len(blocks), 2, r.stdout)
        book, dev = blocks
        self.assertTrue(book.startswith("bookkeeping: admitted by Prolific occupation filter"))
        self.assertIn("18.3% (exact 95% interval 9.5% to 30.4%", book)
        self.assertIn("admission factor: 1.22", book)
        # Reid et al. (2022): 55 of 206 passed, so 151 failed; the label admits 206 / 55 for every pass
        lo, hi = gate_leak.clopper_pearson(151, 206)
        self.assertTrue(dev.startswith("developers: admitted by reported Node.js"))
        self.assertIn("failed the check of the trade: 151", dev)
        self.assertIn(f"73.3% (exact 95% interval {lo:.1%} to {hi:.1%}", dev)
        self.assertIn("admission factor: 3.75", dev)

    def test_csv_with_several_labels_in_a_group(self):
        rows = [[f"A{i:02d}", "bookkeeping", "current role: accountant", 0 if i < 6 else 1] for i in range(40)]
        rows += [[f"K{i:02d}", "bookkeeping", "current role: bookkeeper", 0 if i < 5 else 1] for i in range(20)]
        with tempfile.TemporaryDirectory() as d:
            r = run(GATE, write_csv(d, "answers.csv", ANSWER_HEAD, rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("bookkeeping: admitted by 2 labels", r.stdout)
        self.assertIn("18.3% (exact 95% interval 9.5% to 30.4%", r.stdout)       # the group as a whole
        self.assertIn("current role: accountant: 6 of 40 failed, 15.0%", r.stdout)
        self.assertIn("current role: bookkeeper: 5 of 20 failed, 25.0%", r.stdout)

    def test_nobody_passing_gives_no_finite_factor(self):
        r = run(GATE, "--admitted", 5, "--failed", 5)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("share failing: 100.0%", r.stdout)
        self.assertIn("unbounded", r.stdout)

    def test_bad_input_exits_with_one_line(self):
        good = [["P1", "bookkeeping", "filter", 1], ["P2", "bookkeeping", "filter", 0]]
        cases = {
            "missing column": (ANSWER_HEAD[:3], [r[:3] for r in good], ["answer_correct"]),
            "answer not 1 or 0": (ANSWER_HEAD, good + [["P3", "bookkeeping", "filter", "yes"]], ["row 4", "answer_correct"]),
            "two rows for one person": (ANSWER_HEAD, good + [["P1", "bookkeeping", "filter", 1]], ["P1"]),
            "no rows": (ANSWER_HEAD, [], ["no rows"]),
        }
        for name, (head, rows, needles) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as d:
                one_line_error(self, run(GATE, write_csv(d, "a.csv", head, rows)), *needles)
        for args, needle in (((), "--admitted"), (("--admitted", 60, "--failed", 70), "failed"),
                             (("--admitted", 0, "--failed", 0), "admitted"), (("--admitted", 60), "--failed"),
                             (("no-such-file.csv",), "no-such-file.csv")):
            with self.subTest(args=args):
                one_line_error(self, run(GATE, *args), needle)
        with tempfile.TemporaryDirectory() as d:
            path = write_csv(d, "a.csv", ANSWER_HEAD, good)
            one_line_error(self, run(GATE, path, "--admitted", 60, "--failed", 11), "not both")
            one_line_error(self, run(GATE, path, "--label", "filter"), "admitted_by")


class ProcessStudyAnalysis(unittest.TestCase):
    def test_known_shares_and_effects_are_recovered(self):
        rows = records(planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}}))
        for kind, design in (("wrong_entry", WRONG), ("omission", OMIT)):
            result = process_study.analyse([r for r in rows if r["kind"] == kind], reps=1000, seed=1)
            for cell in CELLS:
                caught, total, people = result["cells"][cell]
                with self.subTest(kind=kind, cell=cell):
                    self.assertEqual((total, people), (100, 20))
                    self.assertAlmostEqual(caught / total, design[cell])
            a1, ap, p1, pp = (design[c] for c in CELLS)
            truth = {"process_newcomers": ap - a1, "experience_one_agent": p1 - a1,
                     "interaction": (pp - p1) - (ap - a1)}
            for name, value in truth.items():
                est, lo, hi = result["effects"][name]
                with self.subTest(kind=kind, effect=name):
                    self.assertAlmostEqual(est, value)
                    self.assertLess(lo, value)
                    self.assertGreater(hi, value)
                    self.assertLess(hi - lo, 0.4)
            gap, reason = process_study.gap_share(result)
            self.assertEqual(reason, "")
            self.assertAlmostEqual(gap[0], (ap - a1) / (p1 - a1))
            self.assertLess(gap[1], gap[0])
            self.assertGreater(gap[2], gap[0])

    def test_gap_share_needs_an_experience_effect_whose_interval_excludes_zero(self):
        result = process_study.analyse([r for r in records(planted({"Day": {"wrong_entry": FLAT}}))], reps=1000)
        est, lo, hi = result["effects"]["experience_one_agent"]
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)
        gap, reason = process_study.gap_share(result)
        self.assertIsNone(gap)
        self.assertIn("includes zero", reason)

    def test_a_reversed_experience_effect_is_not_divided_either(self):
        reverse = dict(zip(CELLS, (0.80, 0.85, 0.40, 0.60)))
        result = process_study.analyse(records(planted({"Day": {"omission": reverse}})), reps=1000)
        self.assertLess(result["effects"]["experience_one_agent"][2], 0)
        gap, reason = process_study.gap_share(result)
        self.assertIsNone(gap)
        self.assertIn("negative", reason)

    def test_a_missing_cell_leaves_its_contrasts_empty(self):
        rows = [r for r in records(planted({"Day": {"omission": OMIT}})) if r["cell"] != ("present", "process")]
        result = process_study.analyse(rows, reps=200)
        self.assertIsNone(result["effects"]["interaction"])
        self.assertIsNotNone(result["effects"]["process_newcomers"])
        self.assertEqual(result["cells"][("present", "process")], (0, 0, 0))


class ProcessStudyCli(unittest.TestCase):
    def cli(self, rows, *extra, pieces=None):
        with tempfile.TemporaryDirectory() as d:
            args = [STUDY, write_csv(d, "errors.csv", ERR_HEAD, rows)]
            if pieces is not None:
                args += ["--pieces", write_csv(d, "pieces.csv", PIECE_HEAD, pieces)]
            r = run(*args, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_cells_effects_and_gap_are_printed(self):
        out = self.cli(planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}}), "--reps", "500")
        wrong = block(out, "planted errors of kind wrong_entry, all rungs")
        for cell, text in zip(CELLS, ("50/100", "70/100", "80/100", "85/100")):
            self.assertRegex(wrong, rf"{cell[0]} / {cell[1]} +{text} +20 +{text[:2]}\.0%")
        self.assertIn("process effect among newcomers (absent: process - one_agent): +20.0 points, 95% interval +", wrong)
        self.assertIn("experience effect under one agent (one_agent: present - absent): +30.0 points", wrong)
        self.assertIn(": -15.0 points, 95% interval", wrong)
        self.assertRegex(wrong, r"share of the experience gap the process closes: 67%, 95% interval -?\d+% to \d+%")
        omit = block(out, "planted errors of kind omission, all rungs")
        self.assertRegex(omit, r"share of the experience gap the process closes: 57%, 95% interval")

    def test_gap_share_is_suppressed_when_experience_interval_includes_zero(self):
        out = self.cli(planted({"Day": {"wrong_entry": FLAT, "omission": OMIT}}), "--reps", "500")
        line = [x for x in block(out, "planted errors of kind wrong_entry, all rungs").splitlines()
                if "share of the experience gap" in x][0]
        self.assertIn("not printed", line)
        self.assertIn("includes zero", line)
        self.assertNotRegex(line, r"closes: -?\d")
        self.assertIn("closes: 57%", block(out, "planted errors of kind omission, all rungs"))

    def test_same_seed_same_intervals(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_csv(d, "errors.csv", ERR_HEAD, planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}}))
            a, b, c = (run(STUDY, path, "--seed", seed, "--reps", 300).stdout for seed in (7, 7, 8))
            default = run(STUDY, path).stdout
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertIn("seed 7", a)
        self.assertIn("2000 replicates", default)
        self.assertIn("seed 20261010", default)
        cell_lines = [x for x in a.splitlines() if x.startswith(("  absent / ", "  present / "))]
        self.assertEqual(len(cell_lines), 8)
        self.assertEqual(cell_lines, [x for x in c.splitlines() if x.startswith(("  absent / ", "  present / "))])

    def test_the_two_kinds_are_never_pooled(self):
        rows = planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}})
        out = self.cli(rows, "--reps", "300")
        wrong = block(out, "planted errors of kind wrong_entry, all rungs")
        omit = block(out, "planted errors of kind omission, all rungs")
        self.assertIn("50/100", wrong)
        self.assertIn("20/100", omit)
        self.assertNotIn("70/200", out)                      # what the pooled absent / one_agent cell would show
        titles = re.findall(r"^== (.*) ==$", out, re.M)
        self.assertEqual(titles, ["planted errors of kind wrong_entry, all rungs",
                                  "planted errors of kind omission, all rungs"])
        # every omission caught now: the block of wrong entries stays exactly as it was, intervals included
        changed = [r[:5] + [1] if r[4] == "omission" else r for r in rows]
        out2 = self.cli(changed, "--reps", "300")
        self.assertEqual(block(out2, "planted errors of kind wrong_entry, all rungs"), wrong)
        self.assertNotEqual(block(out2, "planted errors of kind omission, all rungs"), omit)

    def test_by_rung_repeats_the_blocks_in_ladder_order(self):
        rows = planted({"Week": {"wrong_entry": FLAT, "omission": OMIT}, "Day": {"wrong_entry": WRONG, "omission": OMIT}})
        out = self.cli(rows, "--by-rung", "--reps", "300")
        self.assertEqual(re.findall(r"^== (.*) ==$", out, re.M), [
            "planted errors of kind wrong_entry, all rungs", "planted errors of kind omission, all rungs",
            "planted errors of kind wrong_entry, rung Day", "planted errors of kind omission, rung Day",
            "planted errors of kind wrong_entry, rung Week", "planted errors of kind omission, rung Week"])
        self.assertIn("100/200", block(out, "planted errors of kind wrong_entry, all rungs"))
        self.assertIn("80/100", block(out, "planted errors of kind wrong_entry, rung Day"))
        self.assertIn("52/100", block(out, "planted errors of kind wrong_entry, rung Week"))

    def test_verified_pieces_get_their_own_block(self):
        rows = planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}})
        pieces = pieces_rows(dict(zip(CELLS, (0.40, 0.60, 0.70, 0.75))))
        out = self.cli(rows, "--reps", "300", pieces=pieces)
        verified = block(out, "verified pieces, all rungs")
        for text in ("24/60", "36/60", "42/60", "45/60"):
            self.assertIn(text, verified)
        self.assertIn("verified/total", verified)
        self.assertIn("process effect among newcomers (absent: process - one_agent): +20.0 points", verified)

    def test_kind_missing_from_the_input_is_named(self):
        out = self.cli(planted({"Day": {"wrong_entry": WRONG}}), "--reps", "200")
        self.assertIn("no planted errors of this kind", block(out, "planted errors of kind omission, all rungs"))

    def test_bad_input_exits_with_one_line(self):
        good = planted({"Day": {"wrong_entry": WRONG}}, people=2, per_person=1)
        first = good[0][0]
        cases = {
            "unknown kind": (ERR_HEAD, good + [["x1", "absent", "process", "Day", "missing_entry", 1]], ["kind", "missing_entry"]),
            "missing column": (ERR_HEAD[:-1], [r[:-1] for r in good], ["caught"]),
            "unknown rung": (ERR_HEAD, good + [["x1", "absent", "process", "Fortnight", "omission", 1]], ["Fortnight"]),
            "unknown way": (ERR_HEAD, good + [["x1", "absent", "two_agents", "Day", "omission", 1]], ["two_agents"]),
            "unknown experience": (ERR_HEAD, good + [["x1", "some", "process", "Day", "omission", 1]], ["experience"]),
            "caught not 1 or 0": (ERR_HEAD, good + [["x1", "absent", "process", "Day", "omission", 2]], ["caught"]),
            "one person in two cells": (ERR_HEAD, good + [[first, "present", "process", "Day", "omission", 1]], [first]),
            "empty participant": (ERR_HEAD, good + [["", "absent", "process", "Day", "omission", 1]], ["participant"]),
            "no rows": (ERR_HEAD, [], ["no rows"]),
        }
        for name, (head, rows, needles) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as d:
                one_line_error(self, run(STUDY, write_csv(d, "e.csv", head, rows)), *needles)
        with tempfile.TemporaryDirectory() as d:
            errors = write_csv(d, "e.csv", ERR_HEAD, good)
            bad = write_csv(d, "p.csv", PIECE_HEAD, [[first, "present", "one_agent", "Day", 1]])
            one_line_error(self, run(STUDY, errors, "--pieces", bad), first)
            nocol = write_csv(d, "q.csv", PIECE_HEAD[:-1], [[first, "absent", "one_agent", "Day"]])
            one_line_error(self, run(STUDY, errors, "--pieces", nocol), "verified")
            one_line_error(self, run(STUDY, errors, "--reps", 5), "--reps")
            one_line_error(self, run(STUDY, errors, "--power", 0.4, 0.6), "not both")
        one_line_error(self, run(STUDY, "no-such-file.csv"), "no-such-file.csv")
        one_line_error(self, run(STUDY), "--power")

    def test_semicolon_csv_from_a_european_spreadsheet(self):
        rows = planted({"Day": {"wrong_entry": WRONG, "omission": OMIT}})
        with tempfile.TemporaryDirectory() as d:
            comma = write_csv(d, "errors.csv", ERR_HEAD, rows)
            semi = Path(d) / "errors-eu.csv"
            semi.write_text(comma.read_text(encoding="utf-8").replace(",", ";"), encoding="utf-8")
            a, b = run(STUDY, comma, "--reps", 200), run(STUDY, semi, "--reps", 200)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(a.stdout.split("\n\n", 1)[1], b.stdout.split("\n\n", 1)[1])


class Power(unittest.TestCase):
    def test_textbook_values(self):
        # 0.5 against 0.7, two-sided 0.05, power 0.8: 93 per group (Fleiss, without continuity correction)
        need = process_study.n_for_power(0.5, 0.7)
        self.assertEqual(math.ceil(need), 93)
        self.assertAlmostEqual(process_study.power(0.5, 0.7, need), 0.80, places=9)
        # R: power.prop.test(n = 50, p1 = .50, p2 = .75) gives power 0.740
        self.assertAlmostEqual(process_study.power(0.5, 0.75, 50), 0.740, places=3)
        self.assertEqual(process_study.power(0.7, 0.5, 40), process_study.power(0.5, 0.7, 40))

    def test_cli_with_and_without_a_design_effect(self):
        r = run(STUDY, "--power", "0.5", "0.7", "--n", "93")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("power with 93 per cell: 0.80", r.stdout)
        self.assertIn("n per cell for 0.80 power: 93 (372 in the four cells)", r.stdout)
        self.assertNotIn("design effect", r.stdout)
        r = run(STUDY, "--power", "0.4", "0.6", "--per-person", "3", "--icc", "0.2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("n per cell for 0.80 power: 97 (388 in the four cells)", r.stdout)
        self.assertIn("design effect 1.40", r.stdout)
        # 96.9 independent observations times 1.40 is 135.7, so 46 people of 3 each per cell
        self.assertIn("46 people, 138 observations per cell (184 people in the four cells)", r.stdout)

    def test_bad_power_input(self):
        for args, needle in (((0.5, 0.5), "equal"), ((1.2, 0.5), "between 0 and 1"),
                             ((0.4, 0.6, "--n", 0), "--n"), ((0.4, 0.6, "--icc", 1.5), "--icc"),
                             ((0.4, 0.6, "--per-person", 0), "--per-person")):
            with self.subTest(args=args):
                one_line_error(self, run(STUDY, "--power", *args), needle)


class Help(unittest.TestCase):
    def test_both_tools_print_usage(self):
        for tool in (GATE, STUDY):
            with self.subTest(tool=tool.name):
                r = run(tool, "--help")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("usage", r.stdout.lower())

    def test_house_docstring(self):
        for tool in (GATE, STUDY):
            doc = ast.get_docstring(ast.parse(tool.read_text(encoding="utf-8")))
            with self.subTest(tool=tool.name):
                self.assertTrue(doc.startswith(tool.name + ": "))
                for part in ("Teaches:", "Limits:", "Usage:", "Licence: MIT"):
                    self.assertIn(part, doc)


class Kits(unittest.TestCase):
    def text(self, name):
        return (KITS / name).read_text(encoding="utf-8")

    def test_each_kit_opens_like_the_others(self):
        for name in NEW_KITS:
            lines = self.text(name).splitlines()
            with self.subTest(kit=name):
                self.assertTrue(lines[0].startswith("# "))
                self.assertRegex(lines[2], r"^\*Paper: Section .+\*$")
                self.assertRegex(lines[3], r"^\*For: .+\*$")

    def test_trade_screen_goes_with_the_tools(self):
        self.assertIn("trade-screen.md", kits_with_these_tools())

    def test_english_without_long_dashes(self):
        for path in [GATE, STUDY, Path(__file__).resolve()] + [KITS / k for k in kits_with_these_tools()]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertIsNone(re.search("[" + chr(0x400) + "-" + chr(0x4FF) + "]", text))  # Cyrillic
                self.assertNotIn(chr(0x2014), text)                                     # em dash
                self.assertNotIn(chr(0x2013), text)                                     # en dash

    def test_python_3_9_syntax(self):
        for path in (GATE, STUDY, Path(__file__).resolve()):
            with self.subTest(file=path.name):
                ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_log_lines_of_the_checking_process_kit(self):
        text = self.text("checking-process.md")
        lines = [x for x in text.splitlines() if x.startswith('{"person"')]
        if not lines:
            self.skipTest("kits/checking-process.md gives no example log lines")
        stated = {int(n): not neg for n, neg in re.findall(r"Line (\d) is (not )?verified", text)}
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(sorted(stated), list(range(1, len(lines) + 1)))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            loaded = horizon.load(str(path))              # exits on any line the scorer would refuse
        checks = set()
        for i, (line, rec) in enumerate(zip(lines, loaded), 1):
            raw = json.loads(line)
            with self.subTest(line=i):
                self.assertEqual(set(raw) - horizon.OPTIONAL, horizon.KEYS)
                self.assertIn("started", raw)
                self.assertEqual(horizon.verified(rec), stated[i])
                if rec["irreversible"]:                   # another family alone never verifies these
                    self.assertFalse(horizon.verified(dict(rec, check="other_family_with_sources")))
            checks.add((rec["check"], horizon.verified(rec)))
        self.assertIn(("same_family", False), checks)
        self.assertIn(("other_family_with_sources", True), checks)

    def test_quoted_commands_print_what_the_kits_show(self):
        found = 0
        for name in NEW_KITS:
            for quoted in re.findall(r"```[a-z]*\n(\$ python3 tools/.*?)\n```", self.text(name), re.S):
                command, *shown = quoted.splitlines()
                r = run(*shlex.split(command[2:])[1:])
                with self.subTest(kit=name, command=command):
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertEqual(r.stdout.rstrip("\n").splitlines(), shown)
                found += 1
        self.assertGreaterEqual(found, 2)

    def test_files_the_kits_name_exist(self):
        for name in kits_with_these_tools():
            for ref in re.findall(r"`([^`\s]+(?:\.md|\.py|/))`", self.text(name)):
                with self.subTest(kit=name, ref=ref):
                    self.assertTrue((KITS / ref).exists() or (ROOT / ref).exists(), ref)


if __name__ == "__main__":
    unittest.main()
