"""Tools that score registered measurements must read them as registered (predictions/predictions.csv and
predictions/resolve/, frozen on OSF on 9 October 2026). Each test pairs a tool's behaviour with the frozen words it
follows, so a change to either shows. Standard library only, no network: python3 -m unittest"""
import contextlib
import csv
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import liveness  # noqa: E402
import name_race  # noqa: E402

TABLE = ROOT / "predictions" / "predictions.csv"
NAMES_RACE = ROOT / "predictions" / "resolve" / "names-race.md"
NAMES_FILE = ROOT / "tools" / "names-table-a2.txt"


def frozen(pid):
    with TABLE.open(newline="", encoding="utf-8") as fh:
        return next(r for r in csv.DictReader(fh) if r["id"] == pid)


class F27Liveness(unittest.TestCase):
    """F27: a product is retired when it is "unreachable or not updated for 12 months"."""

    def test_the_frozen_words_say_12_months(self):
        self.assertIn("not updated for 12 months", frozen("F27")["measure"])
        self.assertEqual(liveness.MAX_DAYS, 365)

    def run_cli(self, pushed_days_ago, *extra):
        as_of = dt.date(2028, 12, 31)
        pushed = (as_of - dt.timedelta(days=pushed_days_ago)).isoformat() + "T00:00:00Z"
        body = json.dumps({"pushed_at": pushed, "archived": False}).encode()
        with tempfile.TemporaryDirectory() as d:
            sample, out = Path(d) / "sample.csv", Path(d) / "out.csv"
            sample.write_text("name,url\nP1,https://github.com/a/b\n", encoding="utf-8")
            argv = ["liveness.py", str(sample), "--out", str(out), "--as-of", as_of.isoformat(), *extra]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(liveness, "fetch", return_value=(200, body)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                liveness.main()
            with out.open(newline="", encoding="utf-8") as fh:
                return next(csv.DictReader(fh))["alive"]

    def test_by_default_a_repository_pushed_200_days_ago_is_alive(self):
        self.assertEqual(self.run_cli(200), "yes")       # 180 days, the old default, would have retired it

    def test_by_default_a_repository_pushed_400_days_ago_is_retired(self):
        self.assertEqual(self.run_cli(400), "no")

    def test_archived_is_not_in_the_registered_words(self):
        body = json.dumps({"pushed_at": "2028-06-01T00:00:00Z", "archived": True}).encode()
        with mock.patch.object(liveness, "fetch", return_value=(200, body)):
            r = liveness.check("https://github.com/a/b", dt.date(2028, 12, 31), liveness.MAX_DAYS, 5)
        self.assertEqual((r["alive"], r["archived"]), ("yes", "yes"))

    def test_the_window_can_still_be_set(self):
        self.assertEqual(self.run_cli(200, "--max-days", "180"), "no")


class NameRace(unittest.TestCase):
    """The annual race of names counts "OpenAlex (title and abstract), Crossref (title)"."""

    def urls(self):
        seen = []
        with mock.patch.object(name_race, "get_json", side_effect=lambda url, **kw: seen.append(url) or None):
            name_race.openalex_count("agent manager", 2026)
            name_race.crossref_count("agent manager", 2026)
        return [urllib.parse.parse_qs(urllib.parse.urlparse(u).query) for u in seen]

    def test_the_frozen_words(self):
        text = NAMES_RACE.read_text(encoding="utf-8")
        self.assertIn("OpenAlex (title and abstract)", text)
        self.assertIn("Crossref (title)", text)

    def test_openalex_reads_title_and_abstract_only(self):
        openalex, _ = self.urls()
        self.assertEqual(openalex["search.title_and_abstract"], ['"agent manager"'])
        self.assertNotIn("search", openalex)               # the plain parameter also reads full texts
        self.assertEqual(openalex["filter"], ["publication_year:2026"])

    def test_crossref_reads_the_title(self):
        _, crossref = self.urls()
        self.assertEqual(crossref["query.title"], ["agent manager"])
        self.assertNotIn("query.bibliographic", crossref)

    def test_the_list_of_table_a2_reads_and_has_no_name_twice(self):
        names = name_race.read_names(str(NAMES_FILE))
        lowered = [n.lower() for n in names]
        self.assertEqual(len(lowered), len(set(lowered)))
        for name in ("builder", "agent manager", "principal", "agentwright", "guarantor",
                     "verified delegation horizon", "amplification gain", "credential crossover point"):
            self.assertIn(name, lowered)
        self.assertGreaterEqual(len(names), len(name_race.DEFAULT_NAMES))


if __name__ == "__main__":
    unittest.main()
