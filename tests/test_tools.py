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
    def test_rejects_what_horizon_rejects(self):
        bad = piece()
        del bad["outside_help"]
        with tempfile.TemporaryDirectory() as d:
            out = self.node_score(write_log(d, [bad]))
            self.assertTrue(out.startswith("ERROR line 1: unknown [], missing [\"outside_help\"]"), out)
            out = self.node_score(write_log(d, [piece(planted_errors=1, planted_missed=2)]))
            self.assertIn("planted_missed must lie between 0 and planted_errors", out)


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
                 ({"pushed_at": "2027-09-01T00:00:00Z", "archived": True}, "no")]
        for data, alive in cases:
            with self.subTest(data=data), mock.patch.object(liveness, "fetch", return_value=(200, json.dumps(data).encode())) as f:
                self.assertEqual(liveness.check("https://github.com/a/b.git", self.TODAY, 180, 5)["alive"], alive)
                f.assert_called_with("https://api.github.com/repos/a/b", 5)

    def test_plain_url(self):
        for status, alive in [(200, "yes"), (301, "yes"), (404, "no"), (0, "no")]:
            with self.subTest(status=status), mock.patch.object(liveness, "fetch", return_value=(status, b"")):
                self.assertEqual(liveness.check("https://example.org", self.TODAY, 180, 5)["alive"], alive)

    def test_cli_writes_dated_csv(self):
        with tempfile.TemporaryDirectory() as d:
            sample, out = Path(d) / "s.csv", Path(d) / "o.csv"
            sample.write_text("name,url,category\nA,https://a.example,notes\nB,https://b.example,crm\n")
            argv = ["liveness.py", str(sample), "--out", str(out), "--as-of", "2027-10-09"]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(liveness, "fetch", side_effect=[(200, b""), (500, b"")]), \
                    contextlib.redirect_stdout(io.StringIO()) as buf:
                liveness.main()
            rows = list(csv.DictReader(out.open()))
            self.assertEqual([r["alive"] for r in rows], ["yes", "no"])
            self.assertEqual(rows[0]["category"], "notes")
            self.assertIn("1 of 2 alive", buf.getvalue())


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
        for name in ("agent manager", "agentwright", "delegation horizon", "credential crossover"):
            self.assertIn(name, name_race.DEFAULT_NAMES)


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

    def test_suspicious_log_is_flagged(self):
        pieces = [piece(date="2026-09-20", reference_hours=8.2, attention_minutes=60) for _ in range(12)]
        with tempfile.TemporaryDirectory() as d:
            log = write_log(d, pieces)
            r = run([PY, str(TOOLS / "too_clean.py"), str(log), "--as-of", "2026-10-09"])
            self.assertEqual(r.returncode, 1)
            for trace in ("no failed", "just above a rung threshold", "barely vary", "one day"):
                self.assertIn(trace, r.stdout)

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
