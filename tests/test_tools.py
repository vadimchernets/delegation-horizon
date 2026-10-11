"""Tests for the tools and kits of the companion repository (tools/, checker.html, integrations/, kits/).
Standard library only, no network: every call to the outside world is replaced by a stand-in.
Run from the repository root: python3 -m unittest -v"""
import contextlib
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
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PY = sys.executable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS))
import horizon  # noqa: E402
import archive_urls  # noqa: E402
import degree_share  # noqa: E402
import explain  # noqa: E402
import kappa  # noqa: E402
import liveness  # noqa: E402
import log_piece  # noqa: E402
import name_race  # noqa: E402
import too_clean  # noqa: E402

C4 = ROOT / "examples" / "c4-log.jsonl"
NODE = shutil.which("node")


def run(args, stdin="", env=None, cwd=ROOT):
    return subprocess.run(args, input=stdin, capture_output=True, text=True, cwd=cwd, timeout=120,
                          env={**os.environ, **(env or {})})


def piece(**over):
    base = {"person": "P01", "domain": "accounts", "date": "2026-09-01", "reference_hours": 9,
            "reference_basis": "two raters", "attention_minutes": 60, "mode": "stages", "check": "expert",
            "agent_saw_check": False, "passed": True, "irreversible": False, "planted_errors": 0,
            "planted_missed": 0, "outside_help": False}
    base.update(over)
    return base


def write_log(folder, pieces, name="log.jsonl"):
    path = Path(folder) / name
    path.write_text("".join(json.dumps(p) + "\n" for p in pieces), encoding="utf-8")
    return path


def european_csv(source, folder, decimal_comma=False):
    """The same log as a European spreadsheet saves it: semicolons, day.month.year, optionally 9,0 for 9."""
    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    for row in rows[1:]:
        for i, name in enumerate(head):
            if name in ("date", "started") and row[i]:
                y, m, d = row[i].split("-")
                row[i] = f"{d}.{m}.{y}"
            if decimal_comma and name == "reference_hours":
                row[i] = f"{float(row[i]):.1f}".replace(".", ",")
    path = Path(folder) / ("eu-" + Path(source).name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter=";").writerows(rows)
    return path


def us_date_csv(folder):
    """A spreadsheet that turned 2026-07-20 into 7/20/2026 in the first data row."""
    lines = (ROOT / "examples" / "c4-log.csv").read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace("2026-07-20", "7/20/2026")
    path = Path(folder) / "us-dates.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class EveryToolHasHelp(unittest.TestCase):
    def test_help(self):
        for tool in sorted(TOOLS.glob("*.py")):
            with self.subTest(tool=tool.name):
                r = run([PY, str(tool), "--help"])
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("usage", r.stdout.lower())


class Checker(unittest.TestCase):
    """checker.html must give exactly what horizon.py gives."""
    html = (ROOT / "checker.html").read_text(encoding="utf-8")

    def rules(self):
        return json.loads(re.search(r'id="rules">(.*?)</script>', self.html, re.S).group(1))

    def test_rules_match_horizon(self):
        r = self.rules()
        self.assertEqual([tuple(x) for x in r["rungs"]], horizon.RUNGS)
        self.assertEqual(r["planted_from"], horizon.PLANTED_FROM)
        self.assertEqual(r["gain_steps"], horizon.GAIN_STEPS)
        self.assertEqual(r["gain_window"], horizon.GAIN_WINDOW)
        self.assertEqual(r["pass_share"], horizon.PASS_SHARE)
        self.assertEqual(r.get("rater_spread"), getattr(horizon, "RATER_SPREAD", None))
        self.assertEqual(set(r["independent"]), horizon.INDEPENDENT)
        self.assertEqual(set(r["checks"]), horizon.CHECKS)
        self.assertEqual(set(r["modes"]), horizon.MODES)
        self.assertEqual(set(r["keys"]), horizon.KEYS)
        self.assertEqual(set(r["optional"]), horizon.OPTIONAL)

    def test_no_network_in_page(self):
        self.assertNotRegex(self.html, r"(?i)(fetch\(|XMLHttpRequest|<script[^>]+src=|<link[^>]+href=|https?://)")

    def node_score(self, log, as_of="2026-10-09", stable=False):
        js = re.search(r'<script id="scorer">(.*?)</script>', self.html, re.S).group(1)
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "score.js"
            script.write_text(js + "\nvar fs = require('fs'); var s = module.exports(" + json.dumps(self.rules())
                              + ");\ntry { var out = s.score(fs.readFileSync(process.argv[2], 'utf8'), process.argv[3], process.argv[4] === 'stable');"
                              " if (out.length) console.log(out.join('\\n')); }"
                              " catch (e) { console.log('ERROR ' + e.message); }\n", encoding="utf-8")
            return run([NODE, str(script), str(log), as_of, "stable" if stable else ""]).stdout

    @unittest.skipUnless(NODE, "node is not installed; the page logic is compared only where node exists")
    def test_c4_same_as_horizon(self):
        expected = (ROOT / "examples" / "c4-expected.txt").read_text(encoding="utf-8")
        self.assertEqual(self.node_score(C4), expected)
        self.assertEqual(self.node_score(ROOT / "examples" / "c4-log.csv"), expected)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_random_logs_same_as_horizon(self):
        rng = random.Random(20261009)
        checks, modes = sorted(horizon.CHECKS), sorted(horizon.MODES)
        with tempfile.TemporaryDirectory() as d:
            for trial in range(40):
                pieces = []
                for _ in range(rng.randint(1, 40)):
                    planted = rng.choice([0, 0, 1, 2])
                    pieces.append(piece(
                        person=rng.choice(["P01", "P02", "Q9"]), domain=rng.choice(["accounts", "legal drafting"]),
                        date=(dt.date(2025, 10, 1) + dt.timedelta(days=rng.randint(0, 400))).isoformat(),
                        reference_hours=rng.choice([0.5, 1, 2, 8, 8.5, 12, 40, 45, 160, 500, 3.25]),
                        attention_minutes=rng.choice([0, 15, 30, 60, 90, 240, 480]),
                        mode=rng.choice(modes), check=rng.choice(checks),
                        agent_saw_check=rng.random() < 0.1, passed=rng.random() < 0.85,
                        irreversible=rng.random() < 0.1, planted_errors=planted,
                        planted_missed=rng.choice([0, 0, 0, planted]), outside_help=rng.random() < 0.1))
                    extra = pieces[-1]
                    if "rater_hours" in horizon.OPTIONAL and rng.random() < 0.3:
                        extra["rater_hours"] = [rng.choice([4, 8, 9]), rng.choice([8, 10, 16])]
                    if "audit" in horizon.OPTIONAL and rng.random() < 0.2:
                        extra["audit"] = rng.choice(["none", "passed", "failed"])
                    if "revoked" in horizon.OPTIONAL and rng.random() < 0.1:
                        extra["revoked"] = True
                log = write_log(d, pieces, f"t{trial}.jsonl")
                stable = trial % 2 == 1
                py = run([PY, "horizon.py", str(log), "--as-of", "2026-10-09"] + (["--stable"] if stable else [])).stdout
                with self.subTest(trial=trial):
                    self.assertTrue(py.strip())
                    self.assertEqual(self.node_score(log, stable=stable), py)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_ties_round_like_python(self):
        # gain 0.125 and a directive share of 12.5%: Python rounds half to even
        pieces = [piece(date=f"2026-09-{i + 1:02d}", reference_hours=1, attention_minutes=480,
                        mode="one_piece" if i == 0 else "stages") for i in range(8)]
        with tempfile.TemporaryDirectory() as d:
            log = write_log(d, pieces)
            py = run([PY, "horizon.py", str(log), "--as-of", "2026-10-09"]).stdout
            self.assertIn("gain 0.12; directive share 12%", py)
            self.assertIn("median accepted size 1.0 h", py)
            self.assertEqual(self.node_score(log), py)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_reads_a_csv_with_every_column_of_the_template(self):
        # templates/work-log.csv has 22 columns; a spreadsheet leaves the optional ones empty
        self.assertEqual((ROOT / "templates" / "work-log.csv").read_text(encoding="utf-8").strip(),
                         (ROOT / "examples" / "team-log.csv").read_text(encoding="utf-8").splitlines()[0])
        expected = (ROOT / "examples" / "team-expected.txt").read_text(encoding="utf-8")
        self.assertEqual(self.node_score(ROOT / "examples" / "team-log.csv"), expected)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_reads_a_european_spreadsheet_csv(self):
        expected = (ROOT / "examples" / "team-expected.txt").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.node_score(european_csv(ROOT / "examples" / "team-log.csv", d)), expected)
            c4 = european_csv(ROOT / "examples" / "c4-log.csv", d, decimal_comma=True)
            self.assertEqual(self.node_score(c4), (ROOT / "examples" / "c4-expected.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(NODE, "node is not installed")
    def test_an_unreadable_date_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.node_score(us_date_csv(d))
            self.assertTrue(out.startswith("ERROR row 2:"), out)
            self.assertIn("YYYY-MM-DD", out)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_rejects_what_horizon_rejects(self):
        bad = piece()
        del bad["outside_help"]
        with tempfile.TemporaryDirectory() as d:
            out = self.node_score(write_log(d, [bad]))
            self.assertTrue(out.startswith("ERROR line 1: unknown [], missing [\"outside_help\"]"), out)
            out = self.node_score(write_log(d, [piece(planted_errors=1, planted_missed=2)]))
            self.assertIn("planted_missed must lie between 0 and planted_errors", out)


class Explain(unittest.TestCase):
    """explain.py must give reasons for exactly the verdict horizon.py gives."""

    def explain(self, log, *extra):
        r = run([PY, str(TOOLS / "explain.py"), str(log), "--as-of", "2026-10-09", *extra])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_c4_reasons_slack_and_next_rung(self):
        out = self.explain(C4)
        self.assertIn("P07: small-business bookkeeping . Day (8/10) . x2 . 2026-Q4", out)
        self.assertIn("Day holds: 8 of 10 pieces of at least 8 h in the last 91 days verified; 8 needed", out)
        self.assertIn("from 44% to 97%", out)                       # Section 5.8: 8 of 10, exact 95% interval
        self.assertIn("no further failed piece of this size", out)
        self.assertIn("Day holds through 2026-10-18", out)          # the piece closed 2026-07-20 leaves the window
        self.assertIn("Week needs: 0 pieces of at least 40 h in the last 182 days; 6 needed", out)

    def test_team_blockers_are_named_with_their_dates(self):
        out = self.explain(ROOT / "examples" / "team-log.jsonl")
        self.assertIn("irreversible piece closed 2026-08-23 is not verified", out)       # P02, blocks Hour
        self.assertIn("planted error missed in the piece closed 2026-08-10 blocks Week and above until 2027-02-08",
                      out)                                                                # P03

    def test_spreadsheet_log_explains_the_same(self):
        self.assertEqual(self.explain(ROOT / "examples" / "team-log.csv"),
                         self.explain(ROOT / "examples" / "team-log.jsonl"))

    def test_exact_interval_matches_the_paper(self):
        import explain
        low, high = explain.exact_interval(8, 10)
        self.assertEqual((round(low * 100), round(high * 100)), (44, 97))
        self.assertEqual(round(explain.one_sided_lower(3, 3) * 100), 37)            # Section 5.8: three of three

    def test_reasons_agree_with_the_scorer_on_random_logs(self):
        import explain
        rng = random.Random(7)
        checks, modes = sorted(horizon.CHECKS), sorted(horizon.MODES)
        for trial in range(60):
            pieces = []
            for _ in range(rng.randint(1, 45)):
                planted = rng.choice([0, 0, 1, 2])
                pieces.append(dict(piece(
                    date=dt.date(2025, 10, 1) + dt.timedelta(days=rng.randint(0, 400)),
                    reference_hours=rng.choice([1, 2, 8, 9, 40, 45, 160, 500]), mode=rng.choice(modes),
                    check=rng.choice(checks), passed=rng.random() < 0.85, irreversible=rng.random() < 0.1,
                    planted_errors=planted, planted_missed=rng.choice([0, 0, 0, planted]),
                    outside_help=rng.random() < 0.05)))
            as_of = dt.date(2026, 10, 9)
            for name, hours, minimum, days in horizon.RUNGS:
                with self.subTest(trial=trial, rung=name):
                    self.assertEqual(not explain.unmet(pieces, hours, minimum, as_of, days),
                                     horizon.rung_holds(pieces, hours, minimum, as_of, days))


PLANTED = "error_id,kind,where,what,caught_if\nE1,wrong_entry,invoice 14,dated in the wrong year,flagged or corrected\n" \
          "E2,wrong_entry,notes,a cited figure the source lacks,flagged\nE3,omission,accruals,the March utility bill is missing,accrual added\n"


class Planted(unittest.TestCase):
    """tools/planted.py: seal before the hand-over, score by kind after it, summarise a study ledger."""

    def files(self, d, outcome="error_id,caught\nE1,yes\nE2,yes\nE3,no\n"):
        planted, out = Path(d) / "planted.csv", Path(d) / "outcome.csv"
        planted.write_text(PLANTED, encoding="utf-8")
        out.write_text(outcome, encoding="utf-8")
        return planted, out

    def test_seal_then_score_gives_the_log_fields_by_kind(self):
        with tempfile.TemporaryDirectory() as d:
            planted, out = self.files(d)
            seal = run([PY, str(TOOLS / "planted.py"), "seal", str(planted)])
            self.assertEqual(seal.returncode, 0, seal.stderr)
            digest = re.search(r"sha256 ([0-9a-f]{64})", seal.stdout).group(1)
            self.assertIn("3 planted: 2 wrong_entry, 1 omission", seal.stdout)
            r = run([PY, str(TOOLS / "planted.py"), "score", str(planted), str(out), "--seal", digest])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('"planted_errors": 3, "planted_missed": 1', r.stdout)
            self.assertIn("omission: 1 planted, 1 missed", r.stdout)
            self.assertIn("wrong_entry: 2 planted, 0 missed", r.stdout)

    def test_a_list_changed_after_sealing_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            planted, out = self.files(d)
            digest = re.search(r"sha256 ([0-9a-f]{64})",
                               run([PY, str(TOOLS / "planted.py"), "seal", str(planted)]).stdout).group(1)
            planted.write_text(PLANTED.replace("E3,omission", "E3,wrong_entry"), encoding="utf-8")
            r = run([PY, str(TOOLS / "planted.py"), "score", str(planted), str(out), "--seal", digest])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("does not match the seal", r.stderr)

    def test_every_error_needs_an_outcome_and_a_known_kind(self):
        with tempfile.TemporaryDirectory() as d:
            planted, out = self.files(d, outcome="error_id,caught\nE1,yes\nE2,yes\n")
            r = run([PY, str(TOOLS / "planted.py"), "score", str(planted), str(out)])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("E3", r.stderr)
            planted.write_text(PLANTED.replace("omission", "gap"), encoding="utf-8")
            r = run([PY, str(TOOLS / "planted.py"), "seal", str(planted)])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("wrong_entry or omission", r.stderr)

    def test_summary_of_the_section_10_5_comparison(self):
        rows = ["person,experience,way,task_id,error_id,kind,caught"]
        rates = {("no", "one_agent"): (6, 2), ("no", "process"): (7, 6), ("yes", "one_agent"): (8, 4),
                 ("yes", "process"): (9, 8)}       # caught per ten; each cell has 20 wrong entries and 20 omissions
        for (exp, way), (wrong, omit) in rates.items():
            for p in range(5):
                for e in range(4):
                    k = p * 4 + e
                    rows.append(f"{exp}{way}{p},{exp},{way},T{e},W{e},wrong_entry,{'yes' if k % 10 < wrong else 'no'}")
                    rows.append(f"{exp}{way}{p},{exp},{way},T{e},O{e},omission,{'yes' if k % 10 < omit else 'no'}")
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.csv"
            ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
            r = run([PY, str(TOOLS / "planted.py"), "summary", str(ledger), "--draws", "300"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"no\s+one_agent\s+5\s+0\.60 .*0\.20 ")
        self.assertRegex(r.stdout, r"yes\s+process\s+5\s+0\.90 .*0\.80 ")
        # Section 6.5: 0.60 against 0.40 for omissions, 0.70 against 0.80 for wrong entries
        self.assertIn("newcomer with the process minus expert who accepts on sight: wrong_entry -0.10", r.stdout)
        self.assertIn("newcomer with the process minus expert who accepts on sight: omission +0.20", r.stdout)


class Power(unittest.TestCase):
    """tools/power.py reproduces the sample sizes the paper and the kits state."""

    def test_the_papers_numbers(self):
        import power
        self.assertAlmostEqual(power.power(0.5, 0.05, 1500), 0.78, places=2)     # Section 11.2: "about 0.8"
        self.assertAlmostEqual(power.power(0.5, 0.05, 400), 0.29, places=2)      # "only about 30% of the time"
        self.assertAlmostEqual(power.half_width(0.7, 400), 0.064, places=3)      # matched-task kit: "about 6 points"
        self.assertGreater(power.parity_chance(0.7, 0.10, 1500), 0.999)            # F2: lower bound above -10 points
        self.assertEqual(power.n_for_power(0.5, 0.05, 0.8), 1562)

    def test_cli(self):
        r = run([PY, str(TOOLS / "power.py"), "--p", "0.5", "--diff", "0.05", "--n", "1500"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("power 0.78", r.stdout)
        r = run([PY, str(TOOLS / "power.py"), "--p", "0.5", "--diff", "0.05", "--power", "0.8"])
        self.assertIn("1562 per group", r.stdout)


class ReferenceHours(unittest.TestCase):
    def test_two_close_estimates_give_their_geometric_mean(self):
        r = run([PY, str(TOOLS / "reference_hours.py"), "8", "10.5"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("reference hours 9.2 (geometric mean of two estimates 1.31 apart); the piece reaches Day size",
                      r.stdout)
        self.assertIn("rater_hours 8;10.5", r.stdout)

    def test_far_apart_estimates_ask_for_a_third_rater_and_the_median_decides(self):
        r = run([PY, str(TOOLS / "reference_hours.py"), "6", "10"])
        self.assertIn("needs a third rater", r.stdout)
        self.assertNotIn("reference hours", r.stdout)
        r = run([PY, str(TOOLS / "reference_hours.py"), "6", "10", "7"])
        self.assertIn("reference hours 7.0 (median of three", r.stdout)
        self.assertIn("the piece reaches Hour size", r.stdout)            # 7 hours is short of Day's 8

    def test_the_cell_is_read_back_by_the_scorer_rule(self):
        # horizon.py prints "needs third rater" exactly when the estimates are more than 1.5 apart
        import reference_hours
        self.assertFalse(reference_hours.combine([8, 12])[2])
        self.assertTrue(reference_hours.combine([8, 12.1])[2])
        self.assertEqual(horizon.RATER_SPREAD, 1.5)


class SpreadsheetCard(unittest.TestCase):
    """record_card.py reads what spreadsheets really save, and names what it cannot read."""

    def record(self, path):
        r = run([PY, "record_card.py", str(path), "--as-of", "2026-10-09", "--format", "record"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_european_csv_gives_the_same_records(self):
        with tempfile.TemporaryDirectory() as d:
            for name, comma in (("team-log.csv", False), ("c4-log.csv", True)):
                with self.subTest(log=name):
                    eu = european_csv(ROOT / "examples" / name, d, decimal_comma=comma)
                    self.assertEqual(self.record(eu), self.record(ROOT / "examples" / name))

    def test_an_unreadable_date_is_named_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            r = run([PY, "record_card.py", str(us_date_csv(d)), "--as-of", "2026-10-09"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("row 2", r.stderr)
            self.assertIn("YYYY-MM-DD", r.stderr)
            self.assertNotIn("Traceback", r.stderr)


class LogPiece(unittest.TestCase):
    ANSWERS = ["P07", "small-business bookkeeping", "2026-10-01", "2026-10-03", "9", "", "95",
               "stages", "expert", "no", "yes", "no", "0", "0", "no"]

    def test_piped_answers_make_a_line_horizon_reads(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "log.jsonl"
            r = run([PY, str(TOOLS / "log_piece.py"), str(log)], stdin="\n".join(self.ANSWERS) + "\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            rec = horizon.load(str(log))[0]
            self.assertEqual(rec["reference_basis"], "two raters")
            self.assertEqual(rec["started"], "2026-10-01")
            self.assertTrue(horizon.verified(rec))

    def test_bad_answer_is_asked_again(self):
        answers = self.ANSWERS[:4] + ["nine", "9"] + self.ANSWERS[5:]
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "log.jsonl"
            r = run([PY, str(TOOLS / "log_piece.py"), str(log)], stdin="\n".join(answers) + "\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("not accepted", r.stdout)
            self.assertEqual(len(horizon.load(str(log))), 1)

    def test_rule_breaking_line_is_refused(self):
        answers = self.ANSWERS[:12] + ["1", "2", "no"]       # missed more planted errors than planted
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "log.jsonl"
            r = run([PY, str(TOOLS / "log_piece.py"), str(log)], stdin="\n".join(answers) + "\n")
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(log.exists() and log.read_text().strip())

    def test_pending_from_hook(self):
        with tempfile.TemporaryDirectory() as d:
            pending = Path(d) / "pending.jsonl"
            hook = ROOT / "integrations" / "claude-code-hook" / "open-handover.sh"
            for sid in ("s1", "s2"):
                r = run(["bash", str(hook)], stdin=json.dumps({"session_id": sid, "cwd": "/work"}),
                        env={"HORIZON_PENDING": str(pending)})
                self.assertEqual(r.returncode, 0, r.stderr)
            stubs = [json.loads(x) for x in pending.read_text().splitlines()]
            self.assertEqual([s["session"] for s in stubs], ["s1", "s2"])
            log = Path(d) / "log.jsonl"
            # first session: nothing handed over; second: one failed piece (failures are logged too)
            answers = ["no", "yes", "P07", "accounts", dt.date.today().isoformat(), "4", "", "50", "one_piece", "expert",
                       "no", "no", "no", "0", "0", "no"]
            r = run([PY, str(TOOLS / "log_piece.py"), str(log), "--pending", str(pending)],
                    stdin="\n".join(answers) + "\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            recs = horizon.load(str(log))
            self.assertEqual(len(recs), 1)
            self.assertFalse(recs[0]["passed"])
            self.assertEqual(recs[0]["started"], dt.date.today().isoformat())
            self.assertEqual(pending.read_text(), "")

    def test_hook_survives_no_json(self):
        with tempfile.TemporaryDirectory() as d:
            pending = Path(d) / "sub" / "pending.jsonl"
            r = run(["bash", str(ROOT / "integrations" / "claude-code-hook" / "open-handover.sh")],
                    stdin="", env={"HORIZON_PENDING": str(pending)})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(pending.read_text())["started"], dt.date.today().isoformat())

    def test_hook_settings_example_is_json(self):
        cfg = json.loads((ROOT / "integrations" / "claude-code-hook" / "settings-example.json").read_text())
        self.assertIn("open-handover.sh", cfg["hooks"]["SessionEnd"][0]["hooks"][0]["command"])


class Liveness(unittest.TestCase):
    TODAY = dt.date(2027, 10, 9)

    def test_github_repo_recent_old_archived(self):
        cases = [({"pushed_at": "2027-09-01T00:00:00Z"}, "yes"), ({"pushed_at": "2026-01-01T00:00:00Z"}, "no"),
                 ({"pushed_at": "2027-09-01T00:00:00Z", "archived": True}, "yes")]   # F27: archived is not retired
        for data, alive in cases:
            with self.subTest(data=data), mock.patch.object(liveness, "fetch", return_value=(200, json.dumps(data).encode())) as f:
                self.assertEqual(liveness.check("https://github.com/a/b.git", self.TODAY, 180, 5)["alive"], alive)
                f.assert_called_with("https://api.github.com/repos/a/b", 5)
            self.assertEqual(liveness.github_repo("https://www.GitHub.com/a/b/tree/main?tab=x"), "a/b")

    def test_plain_url(self):
        for status, alive in [(200, "yes"), (301, "yes"), (404, "no"), (0, "no"), (403, "unknown"), (503, "unknown")]:
            with self.subTest(status=status), mock.patch.object(liveness, "fetch", return_value=(status, b"")), \
                    mock.patch.object(liveness, "pause"):
                self.assertEqual(liveness.check("https://example.org", self.TODAY, 180, 5)["alive"], alive)

    def test_cli_writes_dated_csv(self):
        with tempfile.TemporaryDirectory() as d:
            sample, out = Path(d) / "s.csv", Path(d) / "o.csv"
            sample.write_text("name,url,category\nA,https://a.example,notes\nB,https://b.example,crm\n")
            argv = ["liveness.py", str(sample), "--out", str(out), "--as-of", "2027-10-09"]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(liveness, "fetch", side_effect=[(200, b""), (404, b"")]), \
                    contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(io.StringIO()):
                liveness.main()
            rows = list(csv.DictReader(out.open()))
            self.assertEqual([r["alive"] for r in rows], ["yes", "no"])
            self.assertEqual(rows[0]["category"], "notes")
            self.assertIn("1 of 2 alive, 1 retired (50.0% of the 2 decided)", buf.getvalue())
            self.assertEqual(rows[0]["as_of"], "2027-10-09")
            self.assertEqual(rows[0]["checked"], dt.date.today().isoformat())

    def test_rate_limit_waits_for_the_reset_and_retries(self):
        limited = (403, b"", {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(10 ** 10)})
        ok = (200, json.dumps({"pushed_at": "2027-09-01T00:00:00Z"}).encode(), {})
        waits = []
        with mock.patch.object(liveness, "fetch", side_effect=[limited, ok]), \
                mock.patch.object(liveness, "pause", side_effect=waits.append), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(liveness.check("https://github.com/a/b", self.TODAY, 365, 5)["alive"], "yes")
        self.assertEqual(waits, [liveness.MAX_WAIT])
        self.assertIn("rate limit", err.getvalue())
        self.assertEqual(liveness.wait_for(429, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"}, 0,
                                           now=1000), 61)

    def test_a_limit_that_never_lifts_is_unknown_not_retired(self):
        with mock.patch.object(liveness, "fetch", return_value=(403, b"", {})), mock.patch.object(liveness, "pause"), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(liveness.check("https://github.com/a/b", self.TODAY, 365, 5)["alive"], "unknown")

    def test_token_from_the_environment(self):
        ok = (200, json.dumps({"pushed_at": "2027-09-01T00:00:00Z"}).encode(), {})
        with mock.patch.dict(liveness.os.environ, {"GITHUB_TOKEN": "t0k"}), \
                mock.patch.object(liveness, "fetch", return_value=ok) as f:
            liveness.check("https://github.com/a/b", self.TODAY, 365, 5)
        self.assertEqual(f.call_args[0][2], {"Authorization": "Bearer t0k"})

    def test_a_push_after_the_scoring_date_goes_to_the_hand_check(self):
        late = (200, json.dumps({"pushed_at": "2027-10-20T00:00:00Z"}).encode())
        with mock.patch.object(liveness, "fetch", return_value=late):
            r = liveness.check("https://github.com/a/b", self.TODAY, 365, 5)
        self.assertEqual(r["alive"], "unknown")
        self.assertIn("updated after the date", r["note"])

    def test_an_address_without_a_scheme_does_not_stop_the_run(self):
        with mock.patch.object(liveness, "pause"):
            self.assertEqual(liveness.fetch("example.com/app", 1)[0], 0)


class NameRace(unittest.TestCase):
    def test_counts_and_urls(self):
        seen = []

        def fake(url, **kw):
            seen.append(url)
            return {"meta": {"count": 7}} if "openalex" in url else {"message": {"total-results": 40}}
        with mock.patch.object(name_race, "get_json", side_effect=fake):
            self.assertEqual(name_race.openalex_count("agent manager", 2026), 7)
            self.assertEqual(name_race.crossref_count("agent manager", 2026, "a@b.org"), 40)
        self.assertIn("publication_year%3A2026", seen[0])
        self.assertIn("%22agent+manager%22", seen[0])
        self.assertIn("mailto=a%40b.org", seen[1])

    def test_optional_key_from_environment_only(self):
        seen = []
        with mock.patch.object(name_race, "get_json", side_effect=lambda url, **kw: seen.append(url) or None), \
                mock.patch.dict(os.environ, {"OPENALEX_API_KEY": "k123"}):
            name_race.openalex_count("x", 2026)
        self.assertIn("api_key=k123", seen[0])

    def test_rate_limit_is_reported_not_hidden(self):
        err = urllib.error.HTTPError("https://api.openalex.org/works", 429, "Too Many", {},
                                     io.BytesIO(b'{"error":"Rate limit exceeded"}'))
        with mock.patch("urllib.request.urlopen", side_effect=err), \
                contextlib.redirect_stderr(io.StringIO()) as buf:
            self.assertIsNone(name_race.get_json("https://api.openalex.org/works?x=1"))
        self.assertIn("rate limit reached", buf.getvalue())

    def test_service_down_gives_empty_cell(self):
        with mock.patch.object(name_race, "get_json", return_value=None):
            self.assertEqual(name_race.openalex_count("x", 2026), "")

    def test_names_file_and_cli(self):
        with tempfile.TemporaryDirectory() as d:
            names, out = Path(d) / "n.txt", Path(d) / "o.csv"
            names.write_text("# comment\nagentwright\n\nAI steward\n")
            argv = ["name_race.py", "--names", str(names), "--from", "2025", "--to", "2026", "--out", str(out),
                    "--pause", "0"]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(name_race, "get_json", return_value={"meta": {"count": 1}, "message": {"total-results": 2}}), \
                    contextlib.redirect_stdout(io.StringIO()):
                name_race.main()
            rows = list(csv.reader(out.open()))
            self.assertEqual(len(rows), 1 + 2 * 2)
            self.assertEqual(rows[1], ["agentwright", "2025", "1", "2"])

    def test_default_names_cover_both_tables(self):
        self.assertEqual(name_race.DEFAULT_NAMES, name_race.read_names(name_race.NAMES_FILE))
        for name in ("agent manager", "agentwright", "verified delegation horizon", "credential crossover point"):
            self.assertIn(name, [n.lower() for n in name_race.DEFAULT_NAMES])


class DegreeShare(unittest.TestCase):
    def test_classify(self):
        cases = {
            "Bachelor's degree in Computer Science required.": "required",
            "BS in Finance or equivalent experience.": "alternative_accepted",
            "A degree is preferred but not required.": "alternative_accepted",
            "College degree or equivalent practical experience": "alternative_accepted",
            "Show us three things you built with agents.": "not_mentioned",
            "": "not_mentioned",
        }
        for text, kind in cases.items():
            with self.subTest(text=text):
                self.assertEqual(degree_share.classify(text), kind)

    def test_cli_by_group(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = Path(d) / "p.csv", Path(d) / "o.csv"
            with p.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["month", "description"])
                w.writerows([["2026-01", "Bachelor's degree required"], ["2026-01", "No degree required"],
                             ["2026-02", "Ship things"], ["2026-02", "Master's degree in law"]])
            r = run([PY, str(TOOLS / "degree_share.py"), str(p), "--text", "description", "--by", "month",
                     "--out", str(out), "--show", "1"])
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = list(csv.reader(out.open()))
            self.assertEqual(rows[1], ["2026-01", "2", "50.0%", "50.0%", "0.0%"])
            self.assertEqual(rows[2], ["2026-02", "2", "50.0%", "0.0%", "50.0%"])
            r = run([PY, str(TOOLS / "degree_share.py"), str(p), "--text", "nope"])
            self.assertNotEqual(r.returncode, 0)


class Kappa(unittest.TestCase):
    def test_textbook_value(self):
        # 50 items: 20 yes/yes, 15 no/no, 5 yes/no, 10 no/yes -> po 0.70, pe 0.50, kappa 0.40
        a = ["yes"] * 20 + ["no"] * 15 + ["yes"] * 5 + ["no"] * 10
        b = ["yes"] * 20 + ["no"] * 15 + ["no"] * 5 + ["yes"] * 10
        po, k = kappa.cohen_kappa(a, b)
        self.assertAlmostEqual(po, 0.70)
        self.assertAlmostEqual(k, 0.40)
        self.assertEqual(kappa.band(k), "fair")

    def test_perfect_and_single_label(self):
        self.assertEqual(kappa.cohen_kappa(["x", "y"], ["x", "y"])[1], 1.0)
        self.assertEqual(kappa.cohen_kappa(["x", "x"], ["x", "x"])[1], 1.0)
        with self.assertRaises(ValueError):
            kappa.cohen_kappa(["x"], [])

    def test_cli_disagreements(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = Path(d) / "c.csv", Path(d) / "dis.csv"
            p.write_text("item,a,b\nT1,acceptance,acceptance\nT2,trust,acceptance\nT3,cost,cost\nT4,,cost\n")
            r = run([PY, str(TOOLS / "kappa.py"), str(p), "--a", "a", "--b", "b", "--id", "item",
                     "--disagreements", str(out)])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("items coded by both: 3", r.stdout)
            rows = list(csv.reader(out.open()))
            self.assertEqual(rows[1][:3], ["T2", "trust", "acceptance"])


class TooClean(unittest.TestCase):
    def test_c4_example_has_failures_so_no_clean_flag(self):
        pieces = horizon.load(str(C4))
        self.assertFalse(any("no failed" in f for f in too_clean.flags(pieces, 10)))

    def test_c4_example_is_flagged_for_sizes_just_above_day(self):
        # Appendix C4 quotes this flag: five of the ten pieces were rated at exactly 8 hours, the floor of Day
        r = run([PY, str(TOOLS / "too_clean.py"), str(C4), "--as-of", "2026-10-09"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("P07: small-business bookkeeping: audit first\n  - 5 of 10 pieces sit just above a rung threshold",
                      r.stdout)

    def test_suspicious_log_is_flagged(self):
        pieces = [piece(date="2026-09-20", reference_hours=8.2, attention_minutes=60) for _ in range(12)]
        with tempfile.TemporaryDirectory() as d:
            log = write_log(d, pieces)
            r = run([PY, str(TOOLS / "too_clean.py"), str(log), "--as-of", "2026-10-09"])
            self.assertEqual(r.returncode, 1)
            for trace in ("no failed", "just above a rung threshold", "barely vary", "one day"):
                self.assertIn(trace, r.stdout)

    def test_identical_sizes_and_one_kind_of_check_are_flagged(self):
        # README, "How to audit a record": identical sizes or every check of one kind is a reason to look closer
        pieces = [dict(piece(date=f"2026-09-{i + 1:02d}", reference_hours=40, attention_minutes=100 + 37 * i,
                             check="hidden_tests", passed=i != 4, planted_errors=1)) for i in range(10)]
        out = too_clean.flags([dict(p, date=dt.date.fromisoformat(p["date"])) for p in pieces], 10)
        self.assertIn("reference hours barely vary between pieces", out)
        self.assertIn("every piece was checked by one kind of check (hidden_tests)", out)
        c4 = too_clean.flags(horizon.load(str(C4)), 10)
        self.assertFalse(any("barely vary" in f or "one kind" in f for f in c4), c4)

    def test_small_logs_are_skipped(self):
        self.assertEqual(too_clean.flags([piece()] * 3, 10), [])

    def test_weak_checks_and_no_planted_errors(self):
        pieces = [piece(date=f"2026-09-{i + 1:02d}", reference_hours=45 + i * 7, attention_minutes=30 + i * 40,
                        check="self_review" if i % 2 else "expert", passed=i != 3) for i in range(10)]
        out = too_clean.flags([dict(p, date=dt.date.fromisoformat(p["date"])) for p in pieces], 10)
        self.assertTrue(any("same_family, self_review or none" in f for f in out))
        self.assertTrue(any("none with a planted error" in f for f in out))


class ArchiveUrls(unittest.TestCase):
    def test_fills_missing_keeps_existing(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Path(d) / "claims.csv"
            reg.write_text("claim_id,url,archive_url\nC1,https://a.example,\n"
                           "C2,https://b.example,https://web.archive.org/web/1/b\nC3,not a url,\n")
            with mock.patch.object(sys, "argv", ["archive_urls.py", str(reg), "--pause", "0"]), \
                    mock.patch.object(archive_urls, "save_copy", return_value="https://web.archive.org/web/2/a") as s, \
                    contextlib.redirect_stdout(io.StringIO()):
                archive_urls.main()
            s.assert_called_once_with("https://a.example")
            rows = list(csv.DictReader(reg.open()))
            self.assertEqual([r["archive_url"] for r in rows],
                             ["https://web.archive.org/web/2/a", "https://web.archive.org/web/1/b", ""])

    def test_check_only_uses_lookup(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Path(d) / "claims.csv"
            reg.write_text("url,archive_url\nhttps://a.example,\n")
            with mock.patch.object(sys, "argv", ["archive_urls.py", str(reg), "--check-only"]), \
                    mock.patch.object(archive_urls, "save_copy") as s, \
                    mock.patch.object(archive_urls, "latest_copy", return_value=""), \
                    contextlib.redirect_stdout(io.StringIO()):
                archive_urls.main()
            s.assert_not_called()

    def test_register_template_has_the_columns(self):
        with (ROOT / "sources" / "claims.csv").open(newline="") as fh:
            fields = csv.DictReader(fh).fieldnames
        for col in ("claim_id", "section", "claim", "source", "url", "accessed", "archive_url", "status"):
            self.assertIn(col, fields)


class PrereleaseCheck(unittest.TestCase):
    script = ROOT / "tools" / "prerelease-check.sh"

    def test_syntax(self):
        self.assertEqual(run(["bash", "-n", str(self.script)]).returncode, 0)

    def test_runs_with_no_scanner_installed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "package.json").write_text("{}")
            r = run(["/bin/bash", str(self.script), d], env={"PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("[skip] gitleaks", r.stdout)
            self.assertIn("[skip] npm audit", r.stdout)
            self.assertIn("Who answers when it breaks", r.stdout)


class HouseRules(unittest.TestCase):
    """Everything published here is English, without long dashes and without curriculum material."""
    FILES = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
             and p.suffix in {".py", ".md", ".html", ".sh", ".json", ".csv", ".yml", ".txt", ".cff"}]

    def test_no_cyrillic_no_em_dash(self):
        for p in self.FILES:
            text = p.read_text(encoding="utf-8")
            with self.subTest(file=str(p.relative_to(ROOT))):
                self.assertIsNone(re.search(r"[\u0400-\u04ff]", text))
                self.assertNotIn("\N{EM DASH}", text)

    def test_every_kit_is_listed_in_the_map(self):
        index = (ROOT / "kits" / "README.md").read_text(encoding="utf-8")
        for p in (ROOT / "kits").iterdir():
            if p.name != "README.md":
                with self.subTest(kit=p.name):
                    self.assertIn(p.name + ("/" if p.is_dir() else ""), index)

if __name__ == "__main__":
    unittest.main()
