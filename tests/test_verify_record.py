"""Tests for tools/verify_record.py: the receiving side of a portable record (Sections 6.2 and 10.3).
Standard library only, no network: python3 -m unittest tests.test_verify_record"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TOOL = ROOT / "tools" / "verify_record.py"
AS_OF = "2026-10-09"


def run(*args):
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=120)


class VerifyRecord(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def record(self, log, name="record.json"):
        """A portable record written by record_card.py, exactly as a holder would send it."""
        out = self.tmp / name
        r = run("record_card.py", log, "--as-of", AS_OF, "--format", "json", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        return out

    def copy_of(self, path, name, change=lambda text: text):
        target = self.tmp / name
        target.write_text(change(Path(ROOT / path).read_text(encoding="utf-8")), encoding="utf-8")
        return target

    def test_worked_example_matches(self):
        rec = self.record("examples/c4-log.jsonl")
        r = run(TOOL, rec, "examples/c4-log.jsonl")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("MATCH: P07 / small-business bookkeeping . Day . x2 . 2026-Q4", r.stdout)
        self.assertIn("log: the file that was scored", r.stdout)
        self.assertIn("scorer: the same horizon.py", r.stdout)

    def test_team_spreadsheet_every_record_matches(self):
        rec = self.record("examples/team-log.csv")
        r = run(TOOL, rec, "examples/team-log.csv")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("MATCH: "), 5)
        self.assertIn("5 of 5 records match", r.stdout)

    def test_a_changed_rung_is_caught(self):
        rec = self.record("examples/c4-log.jsonl")
        data = json.loads(rec.read_text(encoding="utf-8"))
        data["rung"], data["verified"] = "Week", 9
        rec.write_text(json.dumps(data) + "\n", encoding="utf-8")
        r = run(TOOL, rec, "examples/c4-log.jsonl")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO MATCH", r.stdout)
        self.assertIn("rung: the record says Week, the log gives Day", r.stdout)
        self.assertIn("verified: the record says 9, the log gives 8", r.stdout)

    def test_a_log_without_its_failure_is_caught(self):
        rec = self.record("examples/c4-log.jsonl")
        trimmed = self.copy_of("examples/c4-log.jsonl", "trimmed.jsonl",
                               lambda text: "".join(line + "\n" for line in text.splitlines()
                                                    if '"passed": false' not in line))
        r = run(TOOL, rec, trimmed)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("log: not the file that was scored", r.stdout)
        self.assertIn("rung: the record says Day, the log gives below Hour", r.stdout)

    def test_same_content_in_other_bytes_is_reported_as_such(self):
        rec = self.record("examples/c4-log.jsonl")
        resaved = self.copy_of("examples/c4-log.jsonl", "resaved.jsonl", lambda text: text + "\n")
        r = run(TOOL, rec, resaved)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("log: not the file that was scored", r.stdout)
        self.assertIn("rescored on 2026-10-09: the same record, field by field", r.stdout)

    def test_another_scorer_is_named(self):
        rec = self.record("examples/c4-log.jsonl")
        data = json.loads(rec.read_text(encoding="utf-8"))
        data["scorer"]["sha256"] = "0" * 64
        rec.write_text(json.dumps(data) + "\n", encoding="utf-8")
        r = run(TOOL, rec, "examples/c4-log.jsonl")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("scorer: not the horizon.py that scored the record", r.stdout)

    def test_person_missing_from_the_log(self):
        rec = self.record("examples/c4-log.jsonl")
        r = run(TOOL, rec, "examples/team-log.jsonl")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("the log has no pieces of P07 in small-business bookkeeping", r.stdout)

    def test_malformed_record_is_refused_without_a_traceback(self):
        bad = self.tmp / "bad.json"
        for text in ('{"format": "delegation-horizon-record/1"}\n', "not json at all\n", ""):
            bad.write_text(text, encoding="utf-8")
            r = run(TOOL, bad, "examples/c4-log.jsonl")
            self.assertEqual(r.returncode, 2, (text, r.stdout, r.stderr))
            self.assertNotIn("Traceback", r.stderr)

    def test_unreadable_log_is_refused_without_a_traceback(self):
        rec = self.record("examples/c4-log.jsonl")
        broken = self.tmp / "broken.jsonl"
        broken.write_text('{"person": "P07", "date": "14.09.2026"\n', encoding="utf-8")
        r = run(TOOL, rec, broken)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("the log could not be read", r.stdout + r.stderr)

    def test_log_that_breaks_a_rule_is_refused_with_the_scorers_reason(self):
        rec = self.record("examples/c4-log.jsonl")
        broken = self.copy_of("examples/c4-log.jsonl", "broken-rule.jsonl",
                              lambda text: text.replace('"planted_errors": 0, "planted_missed": 0',
                                                        '"planted_errors": 1, "planted_missed": 2', 1))
        r = run(TOOL, rec, broken)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("the log could not be read: line 1: planted_missed must lie between 0 and planted_errors",
                      r.stdout)

    def test_pretty_printed_record_is_read(self):
        rec = self.record("examples/c4-log.jsonl")
        data = json.loads(rec.read_text(encoding="utf-8"))
        rec.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        r = run(TOOL, rec, "examples/c4-log.jsonl")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
