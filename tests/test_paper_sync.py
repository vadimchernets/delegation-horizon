"""Tests for tools/paper_sync.py, the check that the paper and this repository say the same thing.
A small repository and a small paper are built side by side in a temporary folder: every check passes on them,
and one change per check makes exactly that check fail. The real paper is checked only when it lies next to the
repository; the code is published without it, so on GitHub that test is skipped.
Standard library only. Run from the repository root: python3 -m unittest -v"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "paper_sync.py"
PY = sys.executable
sys.path.insert(0, str(ROOT / "tools"))
import paper_sync  # noqa: E402

CHECKS = ["listing-horizon", "listing-brier", "c4-log", "c4-output", "table-a6", "table-4", "counts",
          "repo-paths", "figures"]
COPIED = ["horizon.py", "brier.py", "examples/c4-log.jsonl", "examples/c4-expected.txt",
          "predictions/predictions.csv"] + sorted(f"predictions/resolve/{p.name}"       # Table A6 names them
                                                  for p in (ROOT / "predictions" / "resolve").glob("*.md"))
UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    """27 -> 'Twenty-seven', as the paper writes a count at the start of a sentence."""
    text = UNITS[n] if n < 20 else TENS[n // 10 - 2] + ("-" + UNITS[n % 10] if n % 10 else "")
    return text.capitalize()


def run(*args):
    return subprocess.run([PY, str(TOOL), *map(str, args)], capture_output=True, encoding="utf-8", cwd=ROOT,
                          timeout=120, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def save(path, text):
    Path(path).write_bytes(text.encode("utf-8"))


def flip(text, start, end):
    """Change one letter near the middle of text[start:end] to its other case: a change of one byte."""
    for i in range((start + end) // 2, end):
        if text[i].isascii() and text[i].isalpha():
            return text[:i] + text[i].swapcase() + text[i + 1:], i
    raise AssertionError("no letter to change")


def line_at(text, pos):
    return text.count("\n", 0, pos) + 1


def build(folder):
    """A small repository and, beside it, a small paper written so that every check passes."""
    folder = Path(folder)
    repo, paper = folder / "repo", folder / "paper" / "paper.md"
    for name in COPIED:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, repo / name)
    (repo / "pilot").mkdir()
    save(repo / "pilot" / "human_raters.py", "# stand-in for a script filed with its registration\n")
    (paper.parent / "figures").mkdir(parents=True)
    for suffix in (".png", ".svg"):
        (paper.parent / "figures" / ("figure-1" + suffix)).write_bytes(b"stand-in")
    with open(repo / "predictions" / "predictions.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    set_a = [r["id"] for r in rows if r["set"] == "A"]
    set_b = [r["id"] for r in rows if r["set"] == "B"]

    def models(r):
        return f"{r['models_geomean_odds']} ({r['models_min']} to {r['models_max']})"

    def text(name):
        return (ROOT / name).read_text(encoding="utf-8")

    lines = [
        "---", 'title: "After the Programmer Divide: a small paper for the tests"', "---", "",
        "## Abstract", "", f"{words(len(rows))} dated predictions are registered.", "",
        "## Executive summary", "",
        f"All {len(rows)} appear in a table. {words(len(set_a))} resolve from public data. "
        f"{words(len(set_b))} need studies registered separately.", "",
        "## 11. Dated predictions", "", "### 11.2 The predictions", "",
        f"Table A6 and the file predictions/predictions.csv give all {len(rows)}. Set A ({len(set_a)} predictions) "
        f"resolves from public data and the files in predictions/. Set B ({len(set_b)} predictions: "
        f"{', '.join(set_b)}) needs studies.", "",
        "**Table 4.** *Three core predictions.*", "",
        "| # | Prediction | Threshold | Final date | p | Models | Data |", "|---|---|---|---|---|---|---|",
    ]
    lines += [f"| {r['id']} | Prediction {r['id']} | A threshold | {r['final_date']} | {r['probability']} | "
              f"{models(r)} | {'public' if r['set'] == 'A' else 'own study'} |" for r in rows[:3]]
    lines += [
        "", "![](figures/figure-1.png){width=16cm}", "",
        "## Appendix C. The measurement instrument", "",
        "### C2. `horizon.py`", "", "The code below is identical, byte for byte, to `horizon.py`.", "",
        "```python", text("horizon.py") + "```", "",
        "### C3. `brier.py`", "", "```python", text("brier.py") + "```", "",
        "### C4. A worked example", "", "The log below holds ten pieces of work.", "",
        "```json", text("examples/c4-log.jsonl") + "```", "",
        "Running `python3 horizon.py work-log.jsonl --as-of 2026-10-09` prints the record:", "",
        "```", text("examples/c4-expected.txt") + "```", "",
        "### C5. The companion repository", "",
        "| Section | Files | What they do |", "|---|---|---|",
        "| C1 to C4 | `horizon.py`, `examples/`, `predictions/predictions.csv` | Scorer, examples, predictions |",
        "| G | `human_raters.py` | Filed with its registration; reads the field `started` and the option `--as-of` |",
        "",
        "## Appendix D. Registration text", "",
        f"**Table A6.** *All {len(rows)} dated predictions.*", "",
        "| # (set) | Prediction | Dates, probability and model forecasts |", "|---|---|---|",
    ]
    def said(r, column):                         # Table A6 prints the registered words, or the declared ones
        return paper_sync.A6_DECLARED.get((r["id"], column), r[column])

    lines += [f"| {r['id']} ({r['set']}) | **{r['prediction']}.** {r['measure']} Baseline: {said(r, 'baseline')} "
              f"| Check: {r['check_date']}. Final date: {r['final_date']}. p = {r['probability']}; models {models(r)}. "
              f"Unresolved if: {r['unresolved_if']}. Fallback: {r['fallback_source']}. Nearest prior or counter "
              f"forecast: {said(r, 'nearest_prior_or_counter_forecast')} |" for r in rows]
    lines += ["", "Note: individual forecasts are in predictions/predictions.csv.", ""]
    save(paper, "\n".join(lines))
    return repo, paper, rows


class SmallPaper(unittest.TestCase):
    """Every check passes on the small paper; one change per check makes exactly that check fail."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo, self.paper, self.rows = build(tmp.name)
        self.text = self.paper.read_text(encoding="utf-8")

    def failing(self):
        """{check: problems} for the checks that fail, after making sure the run itself went right."""
        r = run("--paper", self.paper, "--repo", self.repo, "--json")
        self.assertNotIn("Traceback", r.stderr)
        results = json.loads(r.stdout)
        self.assertEqual([x["name"] for x in results], CHECKS)
        self.assertEqual(r.returncode, 0 if all(x["ok"] for x in results) else 1)
        return {x["name"]: x["problems"] for x in results if not x["ok"]}

    def assertOnlyFails(self, name, line=None, says=None):
        failed = self.failing()
        self.assertEqual(sorted(failed), [name], failed)
        if line is not None:
            self.assertIn(line, [p["line"] for p in failed[name]], failed[name])
        if says is not None:
            self.assertIn(says, " ".join(p["message"] for p in failed[name]))

    def edit(self, old, new):
        """The paper as built, with one change."""
        self.assertIn(old, self.text)
        save(self.paper, self.text.replace(old, new, 1))

    def line_of(self, line):
        return self.text.split("\n").index(line) + 1

    def row(self, start):
        return next(x for x in self.text.split("\n") if x.startswith(start))

    def test_every_check_passes(self):
        self.assertEqual(self.failing(), {})
        r = run("--paper", self.paper, "--repo", self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([x for x in r.stdout.splitlines() if x.startswith(("OK", "FAIL"))],
                         [f"OK {name}" for name in CHECKS])

    def test_one_changed_byte_in_a_listing(self):
        for name, check in (("horizon.py", "listing-horizon"), ("brier.py", "listing-brier")):
            with self.subTest(listing=name):
                listing = (ROOT / name).read_text(encoding="utf-8")
                start = self.text.index(listing)
                changed, pos = flip(self.text, start, start + len(listing))
                save(self.paper, changed)
                self.assertOnlyFails(check, line=line_at(changed, pos))

    def test_a_space_at_the_end_of_a_listing_line(self):
        listing = (ROOT / "horizon.py").read_text(encoding="utf-8")
        pos = self.text.index(listing) + listing.index("\n")
        save(self.paper, self.text[:pos] + " " + self.text[pos:])
        self.assertOnlyFails("listing-horizon", line=line_at(self.text, pos))

    def test_one_changed_byte_in_the_repository_file(self):
        target = self.repo / "horizon.py"
        original = target.read_text(encoding="utf-8")
        save(target, flip(original, 0, len(original))[0])
        self.assertOnlyFails("listing-horizon")
        save(target, original[:-1])
        self.assertOnlyFails("listing-horizon", says="newline")
        save(target, original + "\n")
        self.assertOnlyFails("listing-horizon")

    def test_a_changed_field_in_the_c4_log(self):
        log = (ROOT / "examples" / "c4-log.jsonl").read_text(encoding="utf-8").splitlines()
        for index in (0, len(log) - 1):
            for field, value in (("attention_minutes", lambda v: v + 1), ("passed", lambda v: 1 if v else 0)):
                with self.subTest(line=index + 1, field=field):
                    record = json.loads(log[index])
                    record[field] = value(record[field])
                    self.edit(log[index], json.dumps(record))
                    self.assertOnlyFails("c4-log", line=line_at(self.text, self.text.index(log[index])), says=field)

    def test_c4_log_spacing_does_not_matter_but_a_missing_line_does(self):
        log = (ROOT / "examples" / "c4-log.jsonl").read_text(encoding="utf-8").splitlines()
        compact = self.text
        for line in log:
            compact = compact.replace(line, json.dumps(json.loads(line), separators=(",", ":")), 1)
        self.assertNotEqual(compact, self.text)
        save(self.paper, compact)
        self.assertEqual(self.failing(), {})
        self.edit(log[-1] + "\n", "")
        self.assertOnlyFails("c4-log")

    def test_one_changed_character_in_the_c4_output(self):
        expected = (ROOT / "examples" / "c4-expected.txt").read_text(encoding="utf-8")
        start = self.text.index(expected)
        changed, pos = flip(self.text, start, start + len(expected))
        save(self.paper, changed)
        self.assertOnlyFails("c4-output", line=line_at(changed, pos))

    def test_a_changed_cell_in_table_a6(self):
        for r in (self.rows[0], self.rows[-1]):
            row = self.row(f"| {r['id']} (")
            other = "0.01" if r["probability"] != "0.01" else "0.02"
            changes = {
                "probability": (f"p = {r['probability']};", f"p = {other};"),
                "check date": (f"Check: {r['check_date']}.", "Check: 2099 data."),
                "final date": (f"Final date: {r['final_date']}.", "Final date: 1 January 2099."),
                "model range": (f"to {r['models_max']})", "to 0.999)"),
                "set": (f"| {r['id']} ({r['set']}) |", f"| {r['id']} ({'B' if r['set'] == 'A' else 'A'}) |"),
            }
            for what, (old, new) in changes.items():
                with self.subTest(id=r["id"], change=what):
                    self.assertIn(old, row)
                    self.edit(row, row.replace(old, new, 1))
                    self.assertOnlyFails("table-a6", line=self.line_of(row), says=r["id"])

    def test_a_changed_word_in_a_text_cell_of_table_a6(self):
        for r in (self.rows[0], self.rows[-1]):
            row = self.row(f"| {r['id']} (")
            word = r["baseline"].split()[-1]
            with self.subTest(id=r["id"]):
                self.assertIn(r["baseline"], row)
                self.edit(row, row.replace(r["baseline"], r["baseline"][: -len(word)] + "changed", 1))
                self.assertOnlyFails("table-a6", line=self.line_of(row), says=f"{r['id']}: the baseline")

    def test_a_missing_or_moved_row_in_table_a6(self):
        for r in (self.rows[len(self.rows) // 2], self.rows[-1]):
            with self.subTest(missing=r["id"]):
                self.edit(self.row(f"| {r['id']} (") + "\n", "")
                self.assertOnlyFails("table-a6", says=r["id"])
        first, second = self.row(f"| {self.rows[0]['id']} ("), self.row(f"| {self.rows[1]['id']} (")
        with self.subTest(moved=self.rows[0]["id"]):
            self.edit(first + "\n" + second, second + "\n" + first)
            self.assertOnlyFails("table-a6", says="order")

    def test_a_changed_cell_in_table_4(self):
        r = self.rows[0]
        row = self.row(f"| {r['id']} | ")
        changes = {
            "probability": (f"| {r['probability']} |", "| 0.999 |"),
            "final date": (f"| {r['final_date']} |", "| 1 January 2099 |"),
            "models": (f"to {r['models_max']})", "to 0.999)"),
            "data": ("| public |", "| own study |") if r["set"] == "A" else ("| own study |", "| public |"),
        }
        for what, (old, new) in changes.items():
            with self.subTest(change=what):
                self.assertIn(old, row)
                self.edit(row, row.replace(old, new, 1))
                self.assertOnlyFails("table-4", line=self.line_of(row), says=r["id"])

    def test_a_wrong_count(self):
        n = len(self.rows)
        set_a = [r["id"] for r in self.rows if r["set"] == "A"]
        set_b = [r["id"] for r in self.rows if r["set"] == "B"]
        changes = [
            (f"All {n} appear", f"All {n + 1} appear"),
            (f"{words(len(set_a))} resolve from public data", f"{words(len(set_a) + 1)} resolve from public data"),
            (f"{words(len(set_b))} need studies", f"{words(len(set_b) - 1)} need studies"),
            (f"Set A ({len(set_a)} predictions)", f"Set A ({len(set_a) - 1} predictions)"),
            (f"Set B ({len(set_b)} predictions:", f"Set B ({len(set_b) + 1} predictions:"),
            (f"{words(n)} dated predictions", f"{words(n - 1)} dated predictions"),
            (f"give all {n}.", f"give all {n - 1}."),
            (f"predictions: {', '.join(set_b)})", f"predictions: {', '.join(set_b[:-1])})"),
            (f"{words(len(set_b))} need studies registered separately.", ""),
        ]
        for old, new in changes:
            with self.subTest(change=new or "removed: " + old):
                self.edit(old, new)
                self.assertOnlyFails("counts")

    def test_a_named_file_that_is_not_in_the_repository(self):
        line = self.text.count("\n") + 2
        for sentence in ("See `tools/no_such_tool.py`.", "See `no_such_file.csv`.", "See `nowhere/`.",
                         "Run `python3 no_such_script.py my-log.csv`.", "The queries are in predictions/resolve/F99.md."):
            with self.subTest(sentence=sentence):
                save(self.paper, self.text + "\n" + sentence + "\n")
                self.assertOnlyFails("repo-paths", line=line)

    def test_words_that_are_not_repository_paths_are_left_alone(self):
        save(self.paper, self.text + "\nThe field `started`, the option `--as-of`, the value `same_family`, the count "
             "`Day (8/10)`, the address `https://example.org/a/b.md`, the DOI `10.17605/OSF.IO/VW6P9`, the reader's "
             "own log in `python3 horizon.py my-log.jsonl --as-of 2026-10-09`, a figure `figures/figure-1.png` and "
             "pilot/studies in prose (https://example.org/predictions/gone.md).\n")
        self.assertEqual(self.failing(), {})

    def test_a_figure_without_its_svg(self):
        (self.paper.parent / "figures" / "figure-1.svg").unlink()
        self.assertOnlyFails("figures", line=self.line_of("![](figures/figure-1.png){width=16cm}"), says="figure-1.svg")

    def test_a_missing_figure(self):
        save(self.paper, self.text + "\n![](figures/figure-2.png){width=16cm}\n")
        self.assertOnlyFails("figures", line=self.text.count("\n") + 2, says="figure-2.png")

    def test_nothing_throws_on_a_wrong_paper_or_an_empty_repository(self):
        for paper, repo in ((self.paper, self.paper.parent), (self.paper.parent / "figures" / "figure-1.png", self.repo)):
            with self.subTest(paper=paper.name, repo=repo.name):
                r = run("--paper", paper, "--repo", repo)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stdout + r.stderr)
                self.assertEqual(len([x for x in r.stdout.splitlines() if x.startswith(("OK ", "FAIL "))]), 9)


class FindingThePaper(unittest.TestCase):
    def test_the_paper_next_to_the_repository_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            repo, paper, _ = build(d)
            save(Path(d) / "notes.md", '---\ntitle: "Notes"\n---\n\n## Appendix C. The measurement instrument\n')
            (Path(d) / "drafts").mkdir()
            save(Path(d) / "drafts" / "outline.md", '---\ntitle: "After the Programmer Divide: outline"\n---\n\n## 1.\n')
            self.assertEqual(paper_sync.find_paper(repo), paper.resolve())
            r = run("--repo", repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("paper.md", r.stdout)

    def test_no_paper(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            self.assertIsNone(paper_sync.find_paper(repo))
            r = run("--repo", repo, "--if-present")
            self.assertEqual((r.returncode, r.stderr), (0, ""))
            self.assertIn("no paper", r.stdout)
            r = run("--repo", repo)
            self.assertEqual(r.returncode, 2)
            self.assertIn("no paper", r.stdout)
            r = run("--repo", repo, "--json", "--if-present")
            self.assertEqual((r.returncode, json.loads(r.stdout)), (0, []))
            r = run("--paper", Path(d) / "missing.md", "--repo", repo)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_help(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage", r.stdout.lower())


class RealPaper(unittest.TestCase):
    """The paper lies next to the repository only where it is written; the code is published without it."""

    def test_the_paper_and_the_repository_agree(self):
        paper = paper_sync.find_paper(ROOT)
        if paper is None:
            self.skipTest("the paper is not next to the repository (it is published separately from the code)")
        r = run("--paper", paper, "--json")
        self.assertNotIn("Traceback", r.stderr)
        results = json.loads(r.stdout)
        self.assertEqual([x["name"] for x in results], CHECKS)
        for x in results:
            with self.subTest(check=x["name"]):
                self.assertTrue(x["ok"], x["problems"])
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
