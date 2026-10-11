"""The files registered on OSF on 9 October 2026 must stay byte for byte what was registered.

predictions/registered-SHA256.txt is the manifest filed with the predictions (OSF 10.17605/OSF.IO/VW6P9, file
resolve-SHA256.txt), copied unchanged; pilot/registered-SHA256.txt lists the SHA-256 that OSF reports for the files
filed with the Prolific pre-pilot (OSF 10.17605/OSF.IO/V92R8). Standard library only: python3 -m unittest"""
import hashlib
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_MANIFEST = ROOT / "predictions" / "registered-SHA256.txt"
PILOT_MANIFEST = ROOT / "pilot" / "registered-SHA256.txt"
# SHA-256 of resolve-SHA256.txt as OSF stores it (registration VW6P9): the manifest itself is checked first.
OSF_MANIFEST_SHA = "07810eb7bee9f1e125b6dab87a68361362ec8ffae02f88fe8f241f382ba50c24"
ONLY_ON_OSF = {"resolve.zip"}          # the registered zip of resolve/; its members are checked one by one


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entries(manifest):
    out = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  (\S+)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


class PredictionsAsRegistered(unittest.TestCase):
    def test_manifest_is_the_registered_file(self):
        self.assertEqual(sha(PREDICTIONS_MANIFEST), OSF_MANIFEST_SHA)

    def test_every_registered_file_is_unchanged(self):
        checked = []
        for digest, name in entries(PREDICTIONS_MANIFEST):
            if name in ONLY_ON_OSF:
                continue
            path = ROOT / "predictions" / ("resolve/" + name[2:] if name.startswith("./") else name)
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertEqual(sha(path), digest)
            checked.append(name)
        self.assertEqual(len(checked), 14)          # nothing skipped silently: 10 in resolve/, 4 beside the table

    def test_scorer_says_registered_not_draft(self):
        r = subprocess.run([sys.executable, str(ROOT / "predictions" / "score.py"),
                            str(ROOT / "predictions" / "outcomes-template.csv")],
                           capture_output=True, text=True, cwd=ROOT, timeout=60)
        first = r.stdout.splitlines()[0]
        self.assertIn("10.17605/OSF.IO/VW6P9", first)
        self.assertNotIn("DRAFT", first)

    def test_readmes_do_not_call_the_table_unregistered(self):
        for path in (ROOT / "README.md", ROOT / "predictions" / "README.md"):
            with self.subTest(file=path.name):
                self.assertNotIn("not yet registered", path.read_text(encoding="utf-8"))


class PilotAsRegistered(unittest.TestCase):
    def test_filed_analysis_files_are_unchanged(self):
        found = entries(PILOT_MANIFEST)
        self.assertEqual(sorted(n for _, n in found), ["human_raters.py", "rater_agreement.py", "task-bank-v0.csv"])
        for digest, name in found:
            with self.subTest(file=name):
                self.assertEqual(sha(ROOT / "pilot" / name), digest)


class LineEndsStayAsCommitted(unittest.TestCase):
    """A clone on Windows (core.autocrlf=true) must give the same bytes, or every hash check fails."""

    def test_gitattributes_turns_off_line_end_conversion(self):
        rules = [ln.split() for ln in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
        self.assertIn(["*", "-text"], rules)


if __name__ == "__main__":
    unittest.main()
