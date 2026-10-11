"""Regression tests for the defects an independent review found on 10 October 2026 in the tools added that day.
Each test names the defect it guards. Standard library only, no network: python3 -m unittest tests.test_review_fixes"""
import csv
import datetime as dt
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "pilot"))
import horizon  # noqa: E402
import record_card  # noqa: E402
import explain  # noqa: E402
import too_clean  # noqa: E402
import prolific_to_long as p2l  # noqa: E402

NODE = shutil.which("node")
HEAD = ("person;domain;started;date;reference_hours;reference_basis;attention_minutes;mode;check;agent_saw_check;"
        "passed;irreversible;planted_errors;planted_missed;outside_help")


def run(*args, cwd=ROOT):
    return subprocess.run([PY, "-B", *map(str, args)], capture_output=True, text=True, cwd=cwd, timeout=300)


def page_score(path, as_of="2026-10-09"):
    """checker.html's scorer on a file, as the page reads it."""
    html = (ROOT / "checker.html").read_text(encoding="utf-8")
    js = re.search(r'<script id="scorer">(.*?)</script>', html, re.S).group(1)
    rules = re.search(r'id="rules">(.*?)</script>', html, re.S).group(1)
    with tempfile.TemporaryDirectory() as d:
        script = Path(d) / "score.js"
        script.write_text(js + "\nvar fs = require('fs'); var s = module.exports(" + rules + ");\n"
                          "try { console.log(s.score(fs.readFileSync(process.argv[2], 'utf8'), process.argv[3], false)"
                          ".join('\\n')); } catch (e) { console.log('ERROR ' + e.message); }\n", encoding="utf-8")
        return subprocess.run([NODE, str(script), str(path), as_of], capture_output=True, text=True,
                              timeout=120).stdout


def semicolon_log(folder, hours, minutes="5", n=10):
    path = Path(folder) / "log.csv"
    rows = [HEAD] + [f"P1;notes;{d:02d}.09.2026;{d:02d}.09.2026;{hours};bank;{minutes};stages;expert;no;yes;no;0;0;no"
                     for d in range(1, n + 1)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


class SemicolonNumbers(unittest.TestCase):
    """record_card.py and checker.html read 0.125 in a semicolon file as 125 (review, defect 1)."""

    def test_dot_decimals_are_read_as_decimals(self):
        with tempfile.TemporaryDirectory() as d:
            for text, value in (("0.125", 0.125), ("8.5", 8.5), ("8,5", 8.5), ("1.030,5", 1030.5), ("40", 40)):
                with self.subTest(text=text):
                    rec = record_card.csv_to_records(str(semicolon_log(d, text)))[0]
                    self.assertEqual(rec["reference_hours"], value)

    def test_a_dot_before_three_digits_alone_is_refused_not_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            for text in ("8.125", "1.030"):
                with self.subTest(text=text):
                    r = run("record_card.py", semicolon_log(d, text), "--as-of", "2026-10-09")
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn("without a dot between thousands", r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stderr)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_page_reads_them_the_same_way(self):
        with tempfile.TemporaryDirectory() as d:
            log = semicolon_log(d, "0.125")
            py = run("record_card.py", log, "--as-of", "2026-10-09", "--to-jsonl", Path(d) / "log.jsonl")
            self.assertEqual(py.returncode, 0, py.stderr)
            expected = run("horizon.py", Path(d) / "log.jsonl", "--as-of", "2026-10-09").stdout
            self.assertIn("below Hour (0/0)", expected)
            self.assertEqual(page_score(log).strip(), expected.strip())
            out = page_score(semicolon_log(d, "8.125"))
            self.assertTrue(out.startswith("ERROR"), out)
            self.assertIn("without a dot between thousands", out)


class StringFlags(unittest.TestCase):
    """A JSON log with "passed": "yes" or "irreversible": "no" was scored silently wrong: "no" reads as true."""

    def log(self, folder, **change):
        rows = [piece(f"2026-09-{i + 1:02d}", 8) for i in range(10)]
        rows[0].update(change)
        path = Path(folder) / "log.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return path

    def test_tools_that_read_the_log_refuse_a_quoted_flag(self):
        with tempfile.TemporaryDirectory() as d:
            for key, value in (("passed", "yes"), ("irreversible", "no"), ("agent_saw_check", "false")):
                log = self.log(d, **{key: value})
                for tool in ("record_card.py", "tools/explain.py", "tools/verify_record.py"):
                    with self.subTest(key=key, tool=tool):
                        args = [tool, log, "--as-of", "2026-10-09"] if tool != "tools/verify_record.py" else \
                            [tool, ROOT / "examples" / "c4-log.jsonl", log]
                        if tool == "tools/verify_record.py":
                            rec = Path(d) / "rec.json"
                            run("record_card.py", "examples/c4-log.jsonl", "--as-of", "2026-10-09", "--format", "json",
                                "--out", rec)
                            args = [tool, rec, log]
                        r = run(*args)
                        self.assertNotEqual(r.returncode, 0)
                        self.assertIn(f"{key} must be true or false", r.stdout + r.stderr)
                        self.assertNotIn("Traceback", r.stderr)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_page_refuses_it_too(self):
        with tempfile.TemporaryDirectory() as d:
            out = page_score(self.log(d, irreversible="no"))
            self.assertTrue(out.startswith("ERROR"), out)
            self.assertIn("irreversible must be true or false", out)

    def test_a_proper_log_still_scores(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("record_card.py", self.log(d), "--as-of", "2026-10-09", "--format", "record")
            self.assertEqual(r.stdout, "tools · Day · ×5 · 2026-Q4\n", r.stderr)     # 80 h for 10 h: gain 8


class PageEncoding(unittest.TestCase):
    """checker.html read a Windows-1252 CSV as UTF-8, so Zoe with two different accents became one person (5)."""

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_page_decodes_bytes_as_record_card_does(self):
        rows = ["person,domain,started,date,reference_hours,reference_basis,attention_minutes,mode,check,"
                "agent_saw_check,passed,irreversible,planted_errors,planted_missed,outside_help"]
        for who, n in (("Zo\u00e9", 10), ("Zo\u00e8", 2)):
            rows += [f"{who},caf\u00e9 accounts,2026-09-{i + 1:02d},2026-09-{i + 1:02d},8,bank,60,stages,expert,no,yes,"
                     "no,0,0,no" for i in range(n)]
        raw = ("\r\n".join(rows) + "\r\n").encode("cp1252")
        html = (ROOT / "checker.html").read_text(encoding="utf-8")
        js = re.search(r'<script id="scorer">(.*?)</script>', html, re.S).group(1)
        rules = re.search(r'id="rules">(.*?)</script>', html, re.S).group(1)
        with tempfile.TemporaryDirectory() as d:
            src, script = Path(d) / "log.csv", Path(d) / "page.js"
            src.write_bytes(raw)
            script.write_text(js + "\nvar fs = require('fs'); var s = module.exports(" + rules + ");\n"
                              "var text = s.decode(new Uint8Array(fs.readFileSync(process.argv[2])));\n"
                              "console.log(s.score(text, '2026-10-09', false).join('\\n'));\n", encoding="utf-8")
            page = subprocess.run([NODE, str(script), str(src)], capture_output=True, text=True, timeout=120).stdout
            py = run("record_card.py", src, "--as-of", "2026-10-09", "--to-jsonl", Path(d) / "log.jsonl")
            self.assertEqual(py.returncode, 0, py.stderr)
            expected = run("horizon.py", Path(d) / "log.jsonl", "--as-of", "2026-10-09").stdout
        self.assertIn("Zo\u00e9: caf\u00e9 accounts . Day (10/10)", expected)
        self.assertEqual(page.strip(), expected.strip())


class StrictNumbers(unittest.TestCase):
    """Python took 1_000 and digits of other scripts, the page took 0x10: one strict pattern on both sides (13)."""

    def test_python_refuses_what_is_not_written_as_a_plain_number(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("1_000", "0x10", "\u0663", " ", "8 h"):
                path = Path(d) / "log.csv"
                path.write_text(HEAD.replace(";", ",") + f"\nP1,web,2026-09-01,2026-09-01,{bad},bank,60,stages,expert,"
                                "no,yes,no,0,0,no\n", encoding="utf-8")
                with self.subTest(value=bad):
                    r = run("record_card.py", path, "--as-of", "2026-10-09")
                    self.assertNotEqual(r.returncode, 0, r.stdout)
                    self.assertNotIn("Traceback", r.stderr)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_page_refuses_the_same(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("1_000", "0x10", "\u0663"):
                path = Path(d) / "log.csv"
                path.write_text(HEAD.replace(";", ",") + f"\nP1,web,2026-09-01,2026-09-01,{bad},bank,60,stages,expert,"
                                "no,yes,no,0,0,no\n", encoding="utf-8")
                with self.subTest(value=bad):
                    self.assertTrue(page_score(path).startswith("ERROR"))

    def test_plain_numbers_still_pass_on_both_sides(self):
        with tempfile.TemporaryDirectory() as d:
            for good in ("8", "8.5", ".5", "1e1", "+8"):
                path = Path(d) / "log.csv"
                path.write_text(HEAD.replace(";", ",") + f"\nP1,web,2026-09-01,2026-09-01,{good},bank,60,stages,expert,"
                                "no,yes,no,0,0,no\n", encoding="utf-8")
                with self.subTest(value=good):
                    r = run("record_card.py", path, "--as-of", "2026-10-09", "--to-jsonl", Path(d) / "log.jsonl")
                    self.assertEqual(r.returncode, 0, r.stderr)
                    if NODE:
                        expected = run("horizon.py", Path(d) / "log.jsonl", "--as-of", "2026-10-09").stdout
                        self.assertEqual(page_score(path).strip(), expected.strip())


class ReferenceHours(unittest.TestCase):
    """reference_hours.py rounded 7.98 up to 8, a Day, and accepted a third estimate nobody needed (defects 2, 9)."""

    def test_rounding_never_lifts_a_piece_into_the_next_rung(self):
        for estimates, size, cell in ((("7.5", "8.5"), "Hour", 7.9), (("39", "41"), "Day", 39.9)):
            with self.subTest(estimates=estimates):
                r = run("tools/reference_hours.py", *estimates)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn(f"reaches {size} size", r.stdout)
                logged = float(re.search(r"reference_hours ([\d.]+)", r.stdout).group(1))
                self.assertAlmostEqual(logged, cell)
                self.assertEqual(explain_size(logged), size)

    def test_a_third_estimate_only_when_the_first_two_disagree(self):
        r = run("tools/reference_hours.py", "7", "8", "20")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("a third estimate is not needed", r.stdout + r.stderr)
        r = run("tools/reference_hours.py", "6", "10", "7")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("rater_hours 6;10;7", r.stdout)


def explain_size(hours):
    return next((name for name, h, *_ in horizon.RUNGS if hours >= h), "below Hour")


def piece(date, hours=40, **kw):
    r = {"person": "P1", "domain": "tools", "started": date, "date": date, "reference_hours": hours,
         "reference_basis": "two raters", "attention_minutes": 60, "mode": "stages", "check": "expert",
         "agent_saw_check": False, "passed": True, "irreversible": False, "planted_errors": 0, "planted_missed": 0,
         "outside_help": False}
    r.update(kw)
    return r


def week_log(extra=()):
    rows = [piece("2026-04-15", 2), piece("2026-04-20", planted_errors=1)]
    rows += [piece(d) for d in ("2026-05-10", "2026-06-01", "2026-06-20", "2026-07-01", "2026-07-15")]
    return rows + list(extra)


def loaded(rows):
    return [dict(r, date=dt.date.fromisoformat(r["date"])) for r in rows]


class Explain(unittest.TestCase):
    """explain.py named the wrong piece for a lapse and promised slack a missed planted error takes away (3, 4)."""

    def test_a_lapse_under_the_91_day_rule_is_explained_by_that_rule(self):
        pieces = loaded(week_log())
        self.assertEqual(horizon.horizon(pieces, dt.date(2026, 10, 9)), "Week")
        text = "\n".join(explain.explain(pieces, dt.date(2026, 10, 9))[4])
        self.assertIn("Week holds through 2026-10-13", text)
        self.assertIn("no verified piece of this size in the last 91 days", text)
        self.assertNotIn("2026-04-15", text)            # the 2-hour piece cannot affect Week

    def test_every_lapse_reason_is_a_condition_that_fails_that_day(self):
        rng = random.Random(20261010)
        for _ in range(300):
            rows = [piece((dt.date(2026, 10, 9) - dt.timedelta(days=rng.randint(0, 200))).isoformat(),
                          rng.choice([8, 40, 45]), passed=rng.random() < 0.9,
                          planted_errors=rng.choice([0, 0, 1])) for _ in range(rng.randint(6, 14))]
            pieces = loaded(rows)
            rung = horizon.horizon(pieces, dt.date(2026, 10, 9))
            if rung == "below Hour":
                continue
            last, why = explain.holds_through(pieces, rung, dt.date(2026, 10, 9))
            if last is None:
                continue
            _, hours, minimum, days = explain.rung_row(rung)
            self.assertFalse(horizon.rung_holds(pieces, hours, minimum, last + dt.timedelta(days=1), days))
            self.assertTrue(why)
            self.assertEqual(why, explain.unmet(pieces, hours, minimum, last + dt.timedelta(days=1), days))

    def test_slack_from_week_up_names_the_missed_planted_error(self):
        text = "\n".join(explain.explain(loaded(week_log()), dt.date(2026, 10, 9))[4])
        self.assertIn("none with a missed planted error", text)

    def test_a_very_long_log_does_not_overflow(self):
        rows = [piece((dt.date(2026, 10, 9) - dt.timedelta(days=i % 90)).isoformat(), 1, passed=i % 5 != 0)
                for i in range(1500)]
        out = explain.explain(loaded(rows), dt.date(2026, 10, 9))
        self.assertEqual(out[0], "Hour")

    def test_a_date_in_another_form_is_refused_with_a_message(self):
        for tool in ("tools/explain.py", "record_card.py", "tools/too_clean.py"):
            with self.subTest(tool=tool):
                r = run(tool, "examples/c4-log.jsonl", "--as-of", "09.10.2026")
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("YYYY-MM-DD", r.stderr)
                self.assertNotIn("Traceback", r.stderr)


class TooClean(unittest.TestCase):
    """too_clean.py let one self-reviewed pass hide a log with no failure at all, and could not read a CSV (7, 12)."""

    def test_no_failure_is_flagged_whatever_the_checks(self):
        rows = [piece(f"2026-09-{i + 1:02d}", 2 + i * 3, attention_minutes=20 + 13 * i,
                      check="self_review" if i == 0 else ("expert" if i % 2 else "hidden_tests")) for i in range(12)]
        flags = too_clean.flags(loaded(rows), 10)
        self.assertTrue(any("no failed, rejected or abandoned piece" in f for f in flags), flags)

    def test_the_spreadsheet_log_is_read(self):
        r = run("tools/too_clean.py", "examples/c4-log.csv", "--as-of", "2026-10-09")
        self.assertIn(r.returncode, (0, 1), r.stderr)
        self.assertIn("P07: small-business bookkeeping", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class Planted(unittest.TestCase):
    """planted.py counted " omission" under no kind and let a second outcome row undo a miss (8, 11, 12)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def files(self, listing, outcome):
        (self.tmp / "list.csv").write_text(listing, encoding="utf-8")
        (self.tmp / "out.csv").write_text(outcome, encoding="utf-8")
        return self.tmp / "list.csv", self.tmp / "out.csv"

    def test_a_kind_with_a_space_is_counted_as_that_kind(self):
        lst, out = self.files("error_id,kind,where,what,caught_if\nE1,wrong_entry,a,b,c\nE2, omission,a,b,c\n"
                              "E3, omission ,a,b,c\n", "error_id,caught\nE1,yes\nE2,no\nE3,no\n")
        r = run("tools/planted.py", "score", lst, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("omission: 2 planted, 2 missed", r.stdout)
        self.assertIn('"planted_errors": 3, "planted_missed": 2', r.stdout)

    def test_an_error_recorded_twice_is_refused(self):
        lst, out = self.files("error_id,kind,where,what,caught_if\nE1,wrong_entry,a,b,c\nE2,omission,a,b,c\n",
                              "error_id,caught\nE1,yes\nE2,no\nE2,yes\n")
        r = run("tools/planted.py", "score", lst, out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("E2", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_short_rows_and_missing_columns_give_a_message(self):
        lst, out = self.files("error_id,kind,where,what,caught_if\nE1,wrong_entry,a,b,c\nE2\n",
                              "error_id,caught\nE1,yes\nE2,no\n")
        r = run("tools/planted.py", "seal", lst)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        (self.tmp / "ledger.csv").write_text("experience,way,task_id,error_id,kind,caught\nyes,process,T1,E1,omission,yes\n",
                                             encoding="utf-8")
        r = run("tools/planted.py", "summary", self.tmp / "ledger.csv")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("person", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class Power(unittest.TestCase):
    """power.py gave tracebacks or nonsense on impossible numbers (12)."""

    def test_impossible_numbers_are_refused_with_a_message(self):
        for args in (["--p", "1.5", "--n", "100"], ["--p", "0.5", "--n", "-100"], ["--p", "0.5", "--diff", "0",
                     "--power", "0.8"], ["--p", "0.5", "--diff", "0.05", "--power", "1"], ["--p", "0.5", "--diff", "0.6",
                     "--n", "100"]):
            with self.subTest(args=args):
                r = run("tools/power.py", *args)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertNotIn("Traceback", r.stderr)

    def test_the_papers_numbers_still_come_out(self):
        self.assertIn("power 0.78", run("tools/power.py", "--p", "0.5", "--diff", "0.05", "--n", "1500").stdout)
        self.assertIn("power 0.29", run("tools/power.py", "--p", "0.5", "--diff", "0.05", "--n", "400").stdout)


class RecordCard(unittest.TestCase):
    """record_card.py: non-finite counts gave a traceback; a card below Hour read as if the count were met (10, 12)."""

    def test_non_finite_counts_give_a_message(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("nan", "inf", "1e999"):
                path = Path(d) / "log.csv"
                path.write_text(HEAD.replace(";", ",") + f"\nP1,web,2026-09-01,2026-09-01,8,bank,60,stages,expert,no,yes,"
                                f"no,0,{bad},no\n", encoding="utf-8")
                with self.subTest(value=bad):
                    r = run("record_card.py", path, "--as-of", "2026-10-09")
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn("planted_missed must be a number", r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stderr)

    def test_non_finite_hours_or_minutes_give_a_message(self):
        with tempfile.TemporaryDirectory() as d:
            for column, bad in (("reference_hours", "inf"), ("reference_hours", "1e999"), ("attention_minutes", "Infinity"),
                                ("reference_hours", "nan")):
                cells = {"reference_hours": "8", "attention_minutes": "60", column: bad}
                path = Path(d) / "log.csv"
                path.write_text(HEAD.replace(";", ",") + f"\nP1,web,2026-09-01,2026-09-01,{cells['reference_hours']},"
                                f"bank,{cells['attention_minutes']},stages,expert,no,yes,no,0,0,no\n", encoding="utf-8")
                with self.subTest(column=column, value=bad):
                    r = run("record_card.py", path, "--as-of", "2026-10-09")
                    self.assertNotEqual(r.returncode, 0, r.stdout)
                    self.assertIn(f"{column} must be a number", r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stderr)

    def test_below_hour_card_names_the_irreversible_piece(self):
        r = run("record_card.py", "examples/team-log.jsonl", "--as-of", "2026-10-09", "--person", "P02")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("an irreversible piece is not verified", r.stdout)
        self.assertNotRegex(r.stdout, r"Count behind the rung: 19 of 20 [^\n]*\(16 needed\)\n")


class Prolific(unittest.TestCase):
    """prolific_to_long.py: units by case, a written unit, signs, odd numerals and text float() reads (B1 to B3)."""

    def convert(self, value, unit):
        line = json.dumps({"participant_id": "X1", "responses": {"q1": {
            "type": "free_text_with_unit", "description": "Task BK01: x", "value": value, "unit": unit}}})
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "bk.jsonl"
            src.write_text(line + "\n", encoding="utf-8")
            return p2l.convert("bookkeeping", str(src))[0]["reference_hours"]

    def test_units_by_case_and_as_written(self):
        for value, unit, hours in (("90", "Minutes", 1.5), ("45", "mins", 0.75), ("90 min", "hours", 1.5),
                                   ("2 hours", "minutes", 2.0), ("8", "Hours", 8.0), ("1,200", "MINUTES", 20.0)):
            with self.subTest(value=value, unit=unit):
                self.assertAlmostEqual(self.convert(value, unit), hours)

    def test_answers_that_are_not_one_positive_number_are_dropped(self):
        for value in ("-5", "−5", "1½", "2 days", "1e3", "1_500", "nan", "inf"):
            with self.subTest(value=value):
                kept = self.convert(value, "hours")
                self.assertIsInstance(kept, str)
                with self.assertRaises(ValueError):
                    float(kept)                          # human_raters.py reads it with float() and drops it

    def test_a_leading_decimal_comma(self):
        self.assertEqual(p2l.number(",5"), 0.5)

    def test_labels_do_not_follow_the_public_salt(self):
        demo = [ROOT / "pilot" / "demo" / "prolific-demo-bookkeeping.jsonl",
                ROOT / "pilot" / "demo" / "prolific-demo-webtools.jsonl"]
        rows = p2l.convert("bookkeeping", str(demo[0])) + p2l.convert("webtools", str(demo[1]))
        hashed = sorted({r["rater"] for r in rows})
        names = p2l.relabel([dict(r) for r in rows])
        self.assertEqual(sorted(names.values()), [f"R{i:03d}" for i in range(1, len(hashed) + 1)])
        self.assertNotEqual([names[h] for h in hashed], sorted(names.values()))   # not the order of the hashes

    def test_bad_command_lines_give_a_message(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.jsonl"
            bad.write_text('{"participant_id": "P1", "responses": {\n', encoding="utf-8")
            for args in (["pilot/demo/prolific-demo-bookkeeping.jsonl"], ["bookkeeping=" + str(Path(d) / "none.jsonl")],
                         ["bookkeeping=" + str(bad)]):
                with self.subTest(args=args):
                    r = run("pilot/prolific_to_long.py", Path(d) / "out.csv", *args)
                    self.assertNotEqual(r.returncode, 0)
                    self.assertNotIn("Traceback", r.stderr)


class TableG2(unittest.TestCase):
    """table_g2.py dropped a domain in which everyone was excluded, and stopped on a BOM (B6, B7)."""

    def write(self, text, encoding="utf-8"):
        f = Path(tempfile.mkdtemp()) / "long.csv"
        f.write_text(text, encoding=encoding)
        return f

    def test_a_domain_with_nobody_kept_still_has_its_row(self):
        f = self.write("domain,rater,task_id,reference_hours,attention_ok,competency_ok\n"
                       "bookkeeping,R1,BK01,2,1,1\nbookkeeping,R2,BK01,2.5,1,1\n"
                       "webtools,R3,WT01,3,1,0\nwebtools,R4,WT01,4,1,0\n")
        r = run("pilot/table_g2.py", f, "--format", "csv")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = list(csv.DictReader(io.StringIO(r.stdout)))
        self.assertEqual([x["domain"] for x in rows], ["bookkeeping", "webtools"])
        web = rows[1]
        self.assertEqual((web["admitted"], web["failed_competency"], web["kept"]), ("2", "2", "0"))

    def test_a_bom_or_semicolons_give_a_message(self):
        text = "domain,rater,task_id,reference_hours,attention_ok,competency_ok\nbookkeeping,R1,BK01,2,1,1\n"
        for f in (self.write(text, "utf-8-sig"), self.write(text.replace(",", ";"))):
            with self.subTest(file=f):
                r = run("pilot/table_g2.py", f)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr)

    def test_the_primary_share_is_never_printed_as_the_threshold_it_misses(self):
        sys.path.insert(0, str(ROOT / "pilot"))
        import table_g2
        row = {"domain": "bk", "admitted": 3, "failed_attention": 0, "failed_competency": 0, "kept": 3, "pairs": 3,
               "share": 0.6996, "calibrated": 0.8, "icc": 0.9, "complete": 3, "retest": 1.0, "retest_n": 1,
               "on_rung": 1, "tasks": 1, "model_hits": 0, "model_pairs": 0, "threshold_met": False}
        self.assertIn("0.700 (not met)", table_g2.markdown([row]))

    def test_identical_ratings_give_no_icc_rather_than_a_crash(self):
        f = self.write("domain,rater,task_id,reference_hours,attention_ok,competency_ok\n"
                       + "".join(f"bookkeeping,R{i},BK0{t},2,1,1\n" for i in (1, 2, 3) for t in (1, 2)))
        r = run("pilot/table_g2.py", f, "--format", "csv")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(csv.DictReader(io.StringIO(r.stdout)))[0]["icc"], "nan")

    def test_the_wrong_answers_are_tallied_by_option(self):
        f = self.write("domain,rater,task_id,reference_hours,attention_ok,competency_ok,competency_answer\n"
                       "bookkeeping,R1,BK08,8,1,1,Debit bank\nbookkeeping,R2,BK08,6,1,0,Debit receivable\n"
                       "bookkeeping,R3,BK08,6,1,0,Debit receivable\nbookkeeping,R4,BK08,5,1,0,Something else\n")
        r = run("pilot/screen_compare.py", f, "--reps", "50")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("wrong answers by option: 'Debit receivable' 2, 'Something else' 1", r.stdout)

    def test_screen_compare_refuses_a_bad_number_of_draws(self):
        f = self.write("domain,rater,task_id,reference_hours,attention_ok,competency_ok\nbookkeeping,R1,BK08,2,1,1\n"
                       "bookkeeping,R2,BK08,3,1,0\n")
        for reps in ("0", "-5"):
            with self.subTest(reps=reps):
                r = run("pilot/screen_compare.py", f, "--reps", reps)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
