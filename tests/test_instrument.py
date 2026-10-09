"""Tests for the measurement instrument of "After the Programmer Divide" (Appendix C).
Standard library only: python3 -m unittest -v"""
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT))
import horizon  # noqa: E402

AS_OF = dt.date(2026, 10, 9)
# SHA-256 of the listings as printed in Appendix C2 and C3. If a test below fails, the code here no
# longer matches the paper: correct the paper first, then the code, then these two lines.
PAPER_SHA = {
    "horizon.py": "102c808d0cb38a5f9b3dbc28cfa74f108891fce984425dfd301ac955a7dc5641",
    "brier.py": "c7d4a4faa2582a3ad12ad35fe95861999cad13c3990d9fc297d19e4a2588860d",
}


def run(*args):
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=60)


def piece(days_ago, hours=8, **kw):
    """One record as horizon.load returns it: verified by an expert unless told otherwise."""
    r = {"person": "P01", "domain": "test domain", "date": AS_OF - dt.timedelta(days=days_ago),
         "reference_hours": hours, "reference_basis": "two raters", "attention_minutes": 60,
         "mode": "stages", "check": "expert", "agent_saw_check": False, "passed": True,
         "irreversible": False, "planted_errors": 0, "planted_missed": 0, "outside_help": False}
    r.update(kw)
    return r


def week_log():
    """Six verified pieces of 40 hours in 182 days, one recent, one with a caught planted error."""
    return ([piece(10, 40, planted_errors=2)] +
            [piece(d, 40) for d in (30, 60, 100, 130, 160)])


class PaperListingTest(unittest.TestCase):
    def test_core_files_match_the_paper(self):
        for name, digest in PAPER_SHA.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)


class WorkedExampleTest(unittest.TestCase):
    def test_c4_prints_the_record_in_the_paper(self):
        r = run("horizon.py", "examples/c4-log.jsonl", "--as-of", "2026-10-09")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, (ROOT / "examples" / "c4-expected.txt").read_text(encoding="utf-8"))

    def test_c4_from_the_spreadsheet_gives_the_same_record(self):
        r = run("record_card.py", "examples/c4-log.csv", "--as-of", "2026-10-09", "--format", "record")
        self.assertEqual(r.stdout, "small-business bookkeeping · Day · ×2 · 2026-Q4\n", r.stderr)

    def test_c4_without_the_failed_piece_loses_day(self):
        pieces = [r for r in horizon.load(ROOT / "examples" / "c4-log.jsonl") if r["passed"]]
        self.assertEqual(len(pieces), 9)
        self.assertNotEqual(horizon.horizon(pieces, AS_OF), "Day")


class RuleTest(unittest.TestCase):
    def test_week_holds_on_the_base_log(self):
        self.assertEqual(horizon.horizon(week_log(), AS_OF), "Week")

    def test_missed_planted_error_blocks_week(self):
        log = week_log() + [piece(5, 1, planted_errors=1, planted_missed=1)]   # even on a small piece
        self.assertNotEqual(horizon.horizon(log, AS_OF), "Week")

    def test_missed_planted_error_makes_the_piece_unverified(self):
        self.assertFalse(horizon.verified(piece(1, planted_errors=2, planted_missed=1)))

    def test_week_needs_a_planted_error(self):
        log = [piece(d, 40) for d in (10, 30, 60, 100, 130, 160)]
        self.assertNotEqual(horizon.horizon(log, AS_OF), "Week")

    def test_outside_help_adds_nothing_to_gain(self):
        alone = [piece(1, 10, attention_minutes=60), piece(2, 10, attention_minutes=60)]
        helped = [piece(1, 10, attention_minutes=60), piece(2, 10, attention_minutes=60, outside_help=True)]
        self.assertAlmostEqual(horizon.gain(alone), 10.0)
        self.assertAlmostEqual(horizon.gain(helped), 5.0)       # numerator halves, minutes stay

    def test_failed_piece_counts_only_in_the_denominator(self):
        log = [piece(1, 10, attention_minutes=60), piece(2, 10, attention_minutes=60, passed=False)]
        self.assertAlmostEqual(horizon.gain(log), 5.0)

    def test_requalification_needs_a_recent_piece(self):
        old = [piece(95, 40, planted_errors=1)] + [piece(d, 40) for d in (100, 120, 130, 150, 170)]
        self.assertNotEqual(horizon.horizon(old, AS_OF), "Week")     # nothing in the last 91 days
        fresh = old + [piece(20, 40)]
        self.assertEqual(horizon.horizon(fresh, AS_OF), "Week")

    def test_ninety_one_day_boundary(self):
        edge = [piece(91, 40, planted_errors=1)] + [piece(d, 40) for d in (100, 120, 130, 150, 170)]
        self.assertNotEqual(horizon.horizon(edge, AS_OF), "Week")    # day 91 is outside the window
        inside = [piece(90, 40, planted_errors=1)] + [piece(d, 40) for d in (100, 120, 130, 150, 170)]
        self.assertEqual(horizon.horizon(inside, AS_OF), "Week")

    def test_eight_of_ten_holds_day_seven_does_not(self):
        eight = [piece(d) for d in range(1, 9)] + [piece(9, passed=False), piece(10, check="self_review")]
        self.assertEqual(horizon.horizon(eight, AS_OF), "Day")
        seven = eight[:7] + [piece(8, passed=False), piece(9, passed=False), piece(10, check="self_review")]
        self.assertNotEqual(horizon.horizon(seven, AS_OF), "Day")

    def test_strict_rule_applies_to_irreversible_pieces_only(self):
        reversible_fail = [piece(d) for d in range(1, 10)] + [piece(10, passed=False)]
        self.assertEqual(horizon.horizon(reversible_fail, AS_OF), "Day")        # 9 of 10 is enough
        irreversible_fail = [piece(d) for d in range(1, 10)] + [piece(10, passed=False, irreversible=True)]
        self.assertNotEqual(horizon.horizon(irreversible_fail, AS_OF), "Day")   # that one must pass
        irreversible_pass = [piece(d, irreversible=True) for d in range(1, 9)] + \
                            [piece(9, passed=False), piece(10, passed=False)]
        self.assertEqual(horizon.horizon(irreversible_pass, AS_OF), "Day")

    def test_check_seen_by_agents_does_not_count(self):
        self.assertFalse(horizon.verified(piece(1, agent_saw_check=True)))
        for kind in ("same_family", "self_review", "none"):
            self.assertFalse(horizon.verified(piece(1, check=kind)), kind)

    def test_steps(self):
        self.assertEqual(horizon.step(4.66), "x2")
        self.assertEqual(horizon.step(0.5), "below x1")
        self.assertEqual(horizon.step(None), "n/a")


class LoadTest(unittest.TestCase):
    def write(self, record):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write(json.dumps(record) + "\n")
        f.close()
        return f.name

    def base(self):
        r = piece(1)
        r["date"] = r["date"].isoformat()
        return r

    def test_rejects_unknown_field(self):
        r = self.base(); r["name"] = "Real Name"
        self.assertNotEqual(run("horizon.py", self.write(r)).returncode, 0)

    def test_rejects_more_missed_than_planted(self):
        r = self.base(); r["planted_missed"] = 1
        self.assertNotEqual(run("horizon.py", self.write(r)).returncode, 0)

    def test_rejects_start_after_close(self):
        r = self.base(); r["started"] = "2026-12-01"
        self.assertNotEqual(run("horizon.py", self.write(r)).returncode, 0)

    def test_schema_lists_the_same_fields(self):
        schema = json.loads((ROOT / "log.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["required"]), horizon.KEYS)
        self.assertEqual(set(schema["properties"]), horizon.KEYS | horizon.OPTIONAL)
        self.assertEqual(set(schema["properties"]["check"]["enum"]), horizon.CHECKS)
        self.assertEqual(set(schema["properties"]["mode"]["enum"]), horizon.MODES)

    def test_csv_template_has_the_schema_columns(self):
        with open(ROOT / "templates" / "work-log.csv", newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(set(header), horizon.KEYS | horizon.OPTIONAL)


class CardTest(unittest.TestCase):
    def test_markdown_card(self):
        r = run("record_card.py", "examples/c4-log.jsonl", "--as-of", "2026-10-09", "--format", "md")
        self.assertIn("### small-business bookkeeping · Day · ×2 · 2026-Q4", r.stdout)
        self.assertIn("8 verified, 2 not verified", r.stdout)

    def test_csv_with_bad_yes_no_is_refused(self):
        src = (ROOT / "examples" / "c4-log.csv").read_text(encoding="utf-8").replace(",no,yes,", ",maybe,yes,", 1)
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(src); f.close()
        self.assertNotEqual(run("record_card.py", f.name).returncode, 0)


class ScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "p.csv").write_text("id,probability\nA,0.4\nB,0.7\nC,0.5\n", encoding="utf-8")

    def score(self, outcomes):
        (self.tmp / "o.csv").write_text("id,status,evidence,scored_on\n" + outcomes, encoding="utf-8")
        return run("predictions/score.py", self.tmp / "o.csv", "--predictions", self.tmp / "p.csv")

    def test_toy_brier(self):
        r = self.score("A,came_true,,\nB,did_not,,\nC,unresolved,,\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("A: p=0.40 outcome=1 score=0.360", r.stdout)
        self.assertIn("Brier score over 2 resolved: 0.425", r.stdout)     # (0.36 + 0.49) / 2
        self.assertIn("unresolved or not yet due: C", r.stdout)

    def test_no_prediction_may_be_dropped(self):
        self.assertNotEqual(self.score("A,came_true,,\nB,did_not,,\n").returncode, 0)

    def test_no_prediction_may_be_added(self):
        self.assertNotEqual(self.score("A,1,,\nB,0,,\nC,0,,\nD,1,,\n").returncode, 0)

    def test_frozen_table(self):
        with open(ROOT / "predictions" / "predictions.csv", newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({f"F{n}" for n in range(1, 27)} - set(ids), {"F4"})   # F4 is split into F4a, F4b
        for r in rows:
            self.assertTrue(0 < float(r["probability"]) < 1, r["id"])
            for key in ("prediction", "measure", "check_date", "final_date", "came_true_if", "did_not_come_true_if"):
                self.assertTrue(r[key].strip(), (r["id"], key))
        r = run("predictions/score.py", "predictions/outcomes-template.csv")
        self.assertIn(f"not yet due: {len(rows)}", r.stdout)


class TeamExampleTest(unittest.TestCase):
    def test_team_log_prints_the_expected_lines(self):
        r = run("horizon.py", "examples/team-log.jsonl", "--as-of", AS_OF)
        self.assertEqual(r.stdout, (ROOT / "examples/team-expected.txt").read_text(encoding="utf-8"))

    def test_team_log_shows_every_kind_of_outcome(self):
        text = (ROOT / "examples/team-expected.txt").read_text(encoding="utf-8")
        self.assertIn("P01: financial tools . Week", text)          # six big pieces, planted errors caught
        self.assertIn("P03: grant reporting . Day", text)           # one missed planted error blocks Week
        self.assertIn("P02: clinic scheduling . below Hour", text)  # a failed irreversible piece blocks every rung it reaches

    def test_spreadsheet_and_json_versions_agree(self):
        a = run("record_card.py", "examples/team-log.csv", "--as-of", AS_OF, "--format", "record").stdout
        b = run("record_card.py", "examples/team-log.jsonl", "--as-of", AS_OF, "--format", "record").stdout
        self.assertEqual(a, b)
        self.assertEqual(len(a.splitlines()), 5)


class AuditSampleTest(unittest.TestCase):
    def setUp(self):
        import audit_sample
        import record_card
        self.mod = audit_sample
        self.records = record_card.load_any(str(ROOT / "examples/team-log.jsonl"))

    def test_same_seed_same_sample(self):
        a, seed = self.mod.draw(self.records, AS_OF, 0.2, 7)
        b, _ = self.mod.draw(self.records, AS_OF, 0.2, 7)
        self.assertEqual([n for n, *_ in a], [n for n, *_ in b])
        self.assertEqual(seed, 7)

    def test_default_seed_is_the_date(self):
        _, seed = self.mod.draw(self.records, AS_OF)
        self.assertEqual(seed, 20261009)

    def test_every_group_is_audited_and_only_accepted_pieces(self):
        sample, _ = self.mod.draw(self.records, AS_OF, 0.05)
        groups = {(r["person"], r["domain"]) for _, r, _ in sample}
        self.assertEqual(len(groups), 5)
        self.assertTrue(all(r["passed"] for _, r, _ in sample))
        start = AS_OF - dt.timedelta(days=91)
        self.assertTrue(all(start < r["date"] <= AS_OF for _, r, _ in sample))

    def test_share_sets_the_size(self):
        records = [piece(d) for d in range(1, 41)]
        sample, _ = self.mod.draw(records, AS_OF, 0.25, 1)
        self.assertEqual(len(sample), 10)

    def test_irreversible_pieces_can_be_forced_in(self):
        records = [piece(d, irreversible=(d % 10 == 0)) for d in range(1, 41)]
        sample, _ = self.mod.draw(records, AS_OF, 0.05, 1, all_irreversible=True)
        self.assertEqual(sum(1 for *_, why in sample if why == "irreversible"), 4)

    def test_cli_writes_csv(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "audit.csv"
            r = run("audit_sample.py", "examples/team-log.csv", "--as-of", AS_OF, "--format", "csv", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            with out.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertGreaterEqual(len(rows), 5)


class ExportRecordTest(unittest.TestCase):
    def test_json_records_follow_the_export_schema(self):
        schema = json.loads((ROOT / "export-record.schema.json").read_text(encoding="utf-8"))
        props = schema["properties"]
        r = run("record_card.py", "examples/team-log.csv", "--as-of", AS_OF, "--format", "json")
        lines = [json.loads(x) for x in r.stdout.splitlines()]
        self.assertEqual(len(lines), 5)
        for rec in lines:
            self.assertEqual(set(rec), set(schema["required"]))
            self.assertEqual(set(rec), set(props))
            self.assertIn(rec["rung"], props["rung"]["enum"])
            self.assertIn(rec["gain_step"], props["gain_step"]["enum"])
            self.assertTrue(set(rec["checks"]) <= set(props["checks"]["items"]["enum"]))
            self.assertRegex(rec["quarter"], props["quarter"]["pattern"])
            self.assertRegex(rec["log_sha256"], props["log_sha256"]["pattern"])
            self.assertEqual(rec["scorer"]["sha256"], hashlib.sha256((ROOT / "horizon.py").read_bytes()).hexdigest())
            self.assertEqual(rec["format"], props["format"]["const"])

    def test_json_record_matches_the_record_line(self):
        r = run("record_card.py", "examples/c4-log.jsonl", "--as-of", AS_OF, "--format", "json")
        rec = json.loads(r.stdout)
        self.assertEqual((rec["rung"], rec["gain_step"], rec["quarter"]), ("Day", "x2", "2026-Q4"))


SECRET = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"
                    r"|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
TEXT = {".py", ".md", ".csv", ".json", ".jsonl", ".txt", ".cff", ".yml", ".yaml", ".html", ".sh", ".js", ""}


class HouseRulesTest(unittest.TestCase):
    def test_no_secrets_or_personal_logs(self):
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file() or path.suffix not in TEXT:
                continue
            self.assertIsNone(SECRET.search(path.read_text(encoding="utf-8", errors="replace")), path)
            self.assertFalse(path.name.startswith("my-log"), path)

    def test_public_text_is_english_without_long_dashes(self):
        for path in ROOT.rglob("*"):
            if ".git" in path.parts:
                continue
            if path.is_file() and path.suffix in TEXT:
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search("[\u0400-\u04ff]", text), path)
                self.assertNotIn("\u2014", text, path)


if __name__ == "__main__":
    unittest.main()
