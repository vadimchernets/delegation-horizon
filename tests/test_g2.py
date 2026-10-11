"""Tests for the Prolific pre-pilot of Appendix G2: the conversion of the exports (prolific_to_long.py) and the
registered analysis (human_raters.py) on a file worked out by hand. Table G2 and the screening comparison are
tested in tests/test_pilot.py (table_g2.py, screen_compare.py).
Standard library only: python3 -m unittest"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot"
sys.path.insert(0, str(PILOT))
import prolific_to_long as p2l  # noqa: E402

BANK = PILOT / "task-bank-v0.csv"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")

# pilot/human_raters.py is the analysis script filed with the OSF registration of the Prolific pre-pilot
# (10.17605/OSF.IO/V92R8) on 9 October 2026, before any data were collected; tests/test_registered.py compares it
# with the SHA-256 that OSF reports. The test below runs it on a file worked out by hand.

RIGHT_BK = "Debit bank, credit accounts receivable"
REVERSED = "Debit accounts receivable, credit bank"
OTHER_BK = "Debit sales, credit bank"
RIGHT_WT = "All rows of the left table, with matching rows of the right table or NULLs"
WRONG_WT = "Only the rows that match in both tables"
COLUMNS = ["domain", "rater", "task_id", "reference_hours", "attention_ok", "competency_ok", "competency_answer"]


def run(script, *args):
    """Run a script of pilot/ as a user would."""
    return subprocess.run([sys.executable, str(PILOT / script)] + [str(a) for a in args],
                          capture_output=True, encoding="utf-8", cwd=str(ROOT), env=ENV, timeout=120)


def write_long(path, raters, columns=COLUMNS):
    """A long CSV; raters are (domain, rater, attention_ok, competency_ok, answer, {task_id: hours})."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for domain, who, att, comp, answer, estimates in raters:
            for task, hours in estimates.items():
                row = {"domain": domain, "rater": who, "task_id": task, "reference_hours": hours,
                       "attention_ok": att, "competency_ok": comp, "competency_answer": answer}
                w.writerow([row[c] for c in columns])
    return path


def human_raters_blocks(stdout):
    """What human_raters.py prints, per domain."""
    blocks = {}
    for chunk in stdout.split("\n== ")[1:]:
        lines = chunk.splitlines()
        m = re.fullmatch(r"(.+): (\d+) raters kept, (\d+) excluded, (\d+) rater pairs over (\d+) tasks", lines[0])
        b = {"kept": int(m.group(2)), "excluded": int(m.group(3)), "pairs": int(m.group(4)), "tasks": int(m.group(5))}
        domain = m.group(1)
        m = re.fullmatch(r"pairs within x1\.5: (\S+)  \(registered threshold 0\.70: (met|not met)\)", lines[1])
        b["share"], b["verdict"] = m.groups()
        b["cshare"] = re.fullmatch(r"pairs within x1\.5 after removing each rater's level: (\S+)", lines[2]).group(1)
        m = re.fullmatch(r"ICC\(2,1\) on log hours, (\d+) complete raters: (\S+)", lines[3])
        b["complete"], b["icc"] = int(m.group(1)), m.group(2)
        m = re.fullmatch(r"test-retest within x1\.5: (\S+) \(n=(\d+)\)", lines[4])
        b["retest"], b["retest_n"] = m.group(1), int(m.group(2))
        b["medians"] = {}
        for line in lines[6:]:
            m = re.fullmatch(r"(\S+)  +(\S+)  (.{10})  (.*)", line)
            b["medians"][m.group(1)] = (m.group(2), m.group(3).strip(), m.group(4).strip())
        blocks[domain] = b
    return blocks


# Seven bookkeepers and four developers, worked out by hand.
# bookkeeping: BK005 fails the competency question and BK006 the attention check: 2 excluded. BK004's BK02 is text
# and its BK03 is above 2000 hours, so both are dropped; BK007 gives nothing usable (text, 0, text). Kept: BK001 to
# BK004, 4 raters. BK01 has 4 raters (6 pairs), BK02 and BK03 have 3 each (3 pairs): 12 pairs. Ratios on BK01
# (2, 3, 4, 3): 1.5, 2, 1.5, 1.33, 1, 1.33, five within 1.5; BK02 (8, 10, 12): 1.25, 1.5, 1.2; BK03 (40, 60, 48):
# 1.5, 1.2, 1.25. So 11 of 12 = 0.917, threshold met. Retest of BK03: 40 and 50, 60 and 30, 48 and 48 (BK004 has
# no usable BK03): 2 of 3 = 0.667. Medians: BK01 3.0 (Hour, intended Hour), BK02 10.0 (Day, intended Hour),
# BK03 48.0 (Week, intended Hour): 1 of 3 in the intended rung. Complete raters: BK001 to BK003.
# webtools: WT004 fails both checks: 1 excluded, 3 kept. WT01 (1, 2, 1.5), WT02 (6, 8, 4), WT03 (2, 4, 3): two
# pairs of three within 1.5 on each task, 6 of 9 = 0.667, not met. Retest 2 and 2, 4 and 3, 3 and 6: 0.667.
# Medians 1.5, 6.0 and 3.0, all Hour as intended: 3 of 3.
HAND = [
    ("bookkeeping", "BK001", 1, 1, RIGHT_BK, {"BK01": 2, "BK02": 8, "BK03": 40, "BK03-retest": 50}),
    ("bookkeeping", "BK002", 1, 1, RIGHT_BK, {"BK01": 3, "BK02": 10, "BK03": 60, "BK03-retest": 30}),
    ("bookkeeping", "BK003", 1, 1, RIGHT_BK, {"BK01": 4, "BK02": 12, "BK03": 48, "BK03-retest": 48}),
    ("bookkeeping", "BK004", 1, 1, RIGHT_BK, {"BK01": 3, "BK02": "a few days", "BK03": 2500, "BK03-retest": 20}),
    ("bookkeeping", "BK005", 1, 0, REVERSED, {"BK01": 1, "BK02": 4, "BK03": 10, "BK03-retest": 10}),
    ("bookkeeping", "BK006", 0, 1, RIGHT_BK, {"BK01": 2, "BK02": 8, "BK03": 40, "BK03-retest": 40}),
    ("bookkeeping", "BK007", 1, 1, RIGHT_BK, {"BK01": "?", "BK02": 0, "BK03": "-", "BK03-retest": ""}),
    ("webtools", "WT001", 1, 1, RIGHT_WT, {"WT01": 1, "WT02": 6, "WT03": 2, "WT03-retest": 2}),
    ("webtools", "WT002", 1, 1, RIGHT_WT, {"WT01": 2, "WT02": 8, "WT03": 4, "WT03-retest": 3}),
    ("webtools", "WT003", 1, 1, RIGHT_WT, {"WT01": 1.5, "WT02": 4, "WT03": 3, "WT03-retest": 6}),
    ("webtools", "WT004", 0, 0, WRONG_WT, {"WT01": 0.5, "WT02": 2, "WT03": 1, "WT03-retest": 1}),
]


class Number(unittest.TestCase):
    def test_comma_before_exactly_three_digits_groups_thousands(self):
        for text, value in (("1,200", 1200.0), ("12,345.5", 12345.5), ("2,000", 2000.0),
                            ("1,000,000", 1000000.0), ("about 1,500 minutes", 1500.0)):
            with self.subTest(text=text):
                self.assertEqual(p2l.number(text), value)

    def test_comma_before_one_or_two_digits_is_a_decimal_comma(self):
        for text, value in (("1,5", 1.5), ("7,25", 7.25), ("0,75", 0.75), ("2,5 hours", 2.5)):
            with self.subTest(text=text):
                self.assertEqual(p2l.number(text), value)

    def test_other_answers_read_as_before(self):
        for text, value in (("1.5", 1.5), ("about 8 hours", 8.0), ("40", 40.0), ("8.", 8.0)):
            with self.subTest(text=text):
                self.assertEqual(p2l.number(text), value)
        for text in ("no idea", "", "a day or two", None):
            with self.subTest(text=text):
                self.assertIsNone(p2l.number(text))

    def test_a_leading_point_is_a_fraction(self):
        self.assertEqual(p2l.number(".5"), 0.5)
        self.assertEqual(p2l.number("about .75 of an hour"), 0.75)
        self.assertEqual(p2l.number("approx. 5"), 5.0)

    def test_an_answer_with_two_numbers_is_not_read_as_either(self):
        # a range is not one positive number; read as its first number it would pull every median down
        for text in ("8-10", "8 to 12", "between 6 and 8", "3 hrs 30 min", "1 200"):
            with self.subTest(text=text):
                self.assertIsNone(p2l.number(text))


PIDS = ["5f0c1d2e3a4b5c6d7e8f9a0b", "60a1b2c3d4e5f60718293a4b", "61b2c3d4e5f60718293a4b5c", "62c3d4e5f60718293a4b5c6d"]
DOUBLE_ENTRY = "Competency check (double-entry): a customer pays an invoice into the business bank account. Which entry?"


def submission(pid, attention, competency, estimates, question=DOUBLE_ENTRY):
    """One line of a Prolific Survey Builder export (responses.jsonl), with the keys prolific_to_long.py reads."""
    responses = {
        "q1": {"description": "Attention check: to show that you are reading, choose Twelve.",
               "type": "multiple_choice", "values": [attention]},
        "q2": {"description": question, "type": "multiple_choice", "values": [competency]},
    }
    for i, (task, value, unit) in enumerate(estimates):
        responses[f"q{i + 3}"] = {"description": f"Task {task}: hours of focused work for one qualified professional?",
                                  "type": "free_text_with_unit", "value": value, "unit": unit}
    return json.dumps({"participant_id": pid, "responses": responses})


BOOKKEEPING_EXPORT = [
    submission(PIDS[0], "Twelve", RIGHT_BK, [("BK01", "90", "minutes"), ("BK02", "1,200", "minutes"),
                                             ("BK03", "2", "hours"), ("BK03 (again)", "2,5", "hours")]),
    submission(PIDS[1], "Eleven", RIGHT_BK, [("BK01", "about 3 hours", "hours"), ("BK02", "8 hours", "hours"),
                                             ("BK03", "no idea", "hours")]),
    submission(PIDS[2], "Twelve", REVERSED, [("BK01", "1,5", "hours"), ("BK02", "2,000", "hours"),
                                             ("BK03", "30", "minutes")]),
]
EXPECTED = [  # participant, task_id, reference_hours, attention_ok, competency_ok, competency_answer
    (PIDS[0], "BK01", 1.5, "1", "1", RIGHT_BK), (PIDS[0], "BK02", 20.0, "1", "1", RIGHT_BK),
    (PIDS[0], "BK03", 2.0, "1", "1", RIGHT_BK), (PIDS[0], "BK03-retest", 2.5, "1", "1", RIGHT_BK),
    (PIDS[1], "BK01", 3.0, "0", "1", RIGHT_BK), (PIDS[1], "BK02", 8.0, "0", "1", RIGHT_BK),
    (PIDS[1], "BK03", "no idea", "0", "1", RIGHT_BK),
    (PIDS[2], "BK01", 1.5, "1", "0", REVERSED), (PIDS[2], "BK02", 2000.0, "1", "0", REVERSED),
    (PIDS[2], "BK03", 0.5, "1", "0", REVERSED),
]


def labels_in(rows, expected):
    """Each participant's one plain label, read from the rows: the converter numbers participants in a random order
    (in the order of the salted hashes, anyone holding an ID could estimate its label), so a test can only ask that
    every row of one participant carries the same label and that the labels are R001, R002, ..."""
    labels = {}
    for row, (pid, *_) in zip(rows, expected):
        labels.setdefault(pid, row["rater"])
    return labels


class Conversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, name, lines):
        path = self.dir / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def convert(self, *sources):
        out = self.dir / "long.csv"
        r = run("prolific_to_long.py", out, *sources)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return reader.fieldnames, list(reader), out.read_text(encoding="utf-8") + r.stdout

    def test_one_export_row_by_row(self):
        fields, rows, _ = self.convert(f"bookkeeping={self.export('bk.jsonl', BOOKKEEPING_EXPORT)}")
        self.assertEqual(fields, COLUMNS)
        labels = labels_in(rows, EXPECTED)
        self.assertEqual(sorted(labels.values()), ["R001", "R002", "R003"])
        self.assertEqual(len(rows), len(EXPECTED))
        for row, (pid, task, hours, att, comp, answer) in zip(rows, EXPECTED):
            with self.subTest(participant=pid, task=task):
                self.assertEqual((row["domain"], row["rater"], row["task_id"]), ("bookkeeping", labels[pid], task))
                if isinstance(hours, float):
                    self.assertAlmostEqual(float(row["reference_hours"]), hours)
                else:
                    self.assertEqual(row["reference_hours"], hours)
                self.assertEqual((row["attention_ok"], row["competency_ok"]), (att, comp))
                self.assertEqual(row["competency_answer"], answer)

    def test_no_identifier_and_no_hash_of_one_is_written(self):
        _, rows, written = self.convert(f"bookkeeping={self.export('bk.jsonl', BOOKKEEPING_EXPORT)}")
        self.assertEqual({r["rater"] for r in rows}, {"R001", "R002", "R003"})
        for pid in PIDS[:3]:
            full = hashlib.sha256((p2l.SALT + pid).encode()).hexdigest()
            with self.subTest(participant=pid):
                self.assertNotIn(pid, written)
                self.assertNotIn(full[:10], written)

    def test_the_wrong_answers_can_be_counted(self):
        # Appendix G2: 11 of 60 answered the question of the trade wrongly, 8 of them by reversing the entry
        lines = []
        for i in range(60):
            answer = REVERSED if i < 8 else OTHER_BK if i < 11 else RIGHT_BK
            lines.append(submission(f"pid{i:04d}", "Twelve", answer, [("BK01", "2", "hours")]))
        _, rows, _ = self.convert(f"bookkeeping={self.export('sixty.jsonl', lines)}")
        failed = [r for r in rows if r["competency_ok"] == "0"]
        self.assertEqual(len(failed), 11)
        self.assertEqual(sum(r["competency_answer"] == REVERSED for r in failed), 8)
        self.assertEqual(len({r["rater"] for r in rows}), 60)

    def test_registered_script_reads_the_conversion(self):
        self.convert(f"bookkeeping={self.export('bk.jsonl', BOOKKEEPING_EXPORT)}")
        r = run("human_raters.py", self.dir / "long.csv")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== bookkeeping: 1 raters kept, 2 excluded", r.stdout)

    def test_help(self):
        r = run("prolific_to_long.py", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class Registered(unittest.TestCase):
    def test_human_raters_on_a_file_worked_by_hand(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("human_raters.py", write_long(Path(d) / "hand.csv", HAND), BANK)
        self.assertEqual(r.returncode, 0, r.stderr)
        b = human_raters_blocks(r.stdout)
        bk, wt = b["bookkeeping"], b["webtools"]
        self.assertEqual((bk["kept"], bk["excluded"], bk["pairs"], bk["tasks"]), (4, 2, 12, 3))
        self.assertEqual((bk["share"], bk["verdict"]), ("0.917", "met"))
        self.assertEqual((bk["retest"], bk["retest_n"], bk["complete"]), ("0.667", 3, 3))
        self.assertEqual(bk["medians"]["BK02"], ("10.0", "Day", "Hour"))
        self.assertEqual(bk["medians"]["BK03"], ("48.0", "Week", "Hour"))
        self.assertEqual((wt["kept"], wt["excluded"], wt["pairs"]), (3, 1, 9))
        self.assertEqual((wt["share"], wt["verdict"]), ("0.667", "not met"))
        self.assertEqual((wt["retest"], wt["retest_n"]), ("0.667", 3))
        self.assertEqual(wt["medians"]["WT02"], ("6.0", "Hour", "Hour"))
