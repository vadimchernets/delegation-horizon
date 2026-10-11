#!/usr/bin/env python3
"""paper_sync.py: check that the paper and this repository say the same thing.

Teaches: the paper prints the scorer and the Brier script (Appendix C2, C3) and says they are identical to the files
here, byte for byte; it prints the worked example's log and output (C4), all predictions (Table A6) and ten of them
(Table 4), counts them by set, names files of this repository and embeds figures. Each of those claims becomes one
check, printed as "OK name" or "FAIL name: what differs, with the paper's line number":
listing-horizon, listing-brier, c4-log, c4-output, table-a6, table-4, counts, repo-paths, figures.
Limits: it reads the paper as it is written today (the headings "### C2." to "### C4.", the captions "**Table 4.**"
and "**Table A6.**", cells such as "Check: 2027 data. Final date: 31 December 2028. p = 0.35; models 0.39 (0.25 to
0.65)."); when that wording changes, a FAIL may mean that this reader needs the same change. It checks that a named
file exists, not what the file says. In a backticked command, a bare data file after the script
(`python3 horizon.py work-log.jsonl`) is the reader's own file and is not looked for; in plain text, only paths that
start with a folder of this repository are checked. The paper is published separately: without it the tool says so.
Usage:
  python3 tools/paper_sync.py [--paper PAPER.md] [--repo .] [--json] [--if-present]
Without --paper it looks next to the repository (in its parent folder and the folders inside it) for a Markdown file
whose front matter title starts with "After the Programmer Divide" and which has the heading of Appendix C.
Exit code 0 when every check passes, 1 when one fails, 2 when no paper is found (0 with --if-present).
Licence: MIT
"""
import argparse
import csv
import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
TITLE = "After the Programmer Divide"
APPENDIX_C = "## Appendix C. The measurement instrument"
EXTENSIONS = (".py", ".md", ".csv", ".json", ".jsonl", ".html", ".sh", ".txt")
SCRIPTS = (".py", ".sh")
COLUMNS = ("id", "set", "probability", "check_date", "final_date", "models_geomean_odds", "models_min", "models_max")
DATA_SET = {"public": "A", "own study": "B"}      # the Data column of Table 4 and the set it stands for
SHOWN = 8                                          # problems shown on one FAIL line; --json lists all
# Text columns of predictions.csv that Table A6 prints word for word. Where the paper words a cell differently on
# purpose, the difference is declared here and in the note under Table A6, and the paper's wording is checked instead.
A6_TEXT = ("prediction", "measure", "baseline", "unresolved_if", "fallback_source", "nearest_prior_or_counter_forecast")
A6_DECLARED = {
    ("F4a", "baseline"): "No public baseline; Gartner (Tyagi, 2026, as summarised by Tray.ai, 2026) expects 60% of "
                         "vibe-coded applications retired by 2028, counting all applications",
    ("F4a", "nearest_prior_or_counter_forecast"):
        'Gartner (Tyagi, 2026, as summarised by Tray.ai, 2026): 60% of vibe-coded applications retired by 2028 "as they '
        'fail to deliver the predictable business value"; a broader population than F4a, which counts only accepted '
        'products',
    ("F4b", "nearest_prior_or_counter_forecast"):
        'Gartner (Tyagi, 2026, as summarised by Tray.ai, 2026): 30% of software engineering teams under "material '
        'capacity strain" from maintaining vibe-coded applications built by citizen developers and business users',
}

UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
BIG = r"(?:\d+|(?:%s)(?:-(?:%s))?)" % ("|".join(TENS), "|".join(UNITS[1:10]))   # 41, Forty-one
ANY = r"(?:%s|%s)" % (BIG, "|".join(UNITS))                                       # and also Fourteen


def statement(pattern):
    return re.compile(pattern, re.IGNORECASE)


# (what the paper says, pattern, which count, sections searched (None: everywhere), must be found)
STATEMENTS = [
    ("All N", statement(r"\ball (%s)\b" % BIG), "total", ("## Abstract", "## Executive summary"), True),
    ("all N", statement(r"\ball (\d+)\b"), "total", ("### 11.2",), False),
    ("N resolve from public data", statement(r"\b(%s) resolve from public data\b" % ANY), "A", None, True),
    ("N need studies", statement(r"\b(%s) need studies\b" % ANY), "B", None, True),
    ("Set A (N predictions)", statement(r"\bSet A \((%s) predictions\)" % ANY), "A", None, True),
    ("Set B (N predictions: ...)", statement(r"\bSet B \((%s) predictions(?::\s*([^)]*))?\)" % ANY), "B", None, True),
    ("N dated predictions", statement(r"\b(%s) (?:dated|registered) predictions\b" % BIG), "total", None, False),
    ("the N predictions", statement(r"\bthe (\d+) predictions\b"), "total", None, False),
]
KIND = {"total": "predictions in all", "A": "in Set A", "B": "in Set B"}

A6_ROW = re.compile(r"^\**(?P<id>[A-Za-z]+\d+[A-Za-z]*)\**\s*\(\s*(?P<set>[A-Za-z]+)\s*\)$")
A6_CELL = re.compile(r"Check:\s*(?P<check>.+?)\.\s+Final date:\s*(?P<final>.+?)\.\s+p\s*=\s*(?P<p>[\d.]+)\s*;\s*"
                     r"models\s+(?P<gm>[\d.]+)\s*\(\s*(?P<lo>[\d.]+)\s+to\s+(?P<hi>[\d.]+)\s*\)")
MODELS = re.compile(r"(?P<gm>[\d.]+)\s*\(\s*(?P<lo>[\d.]+)\s+to\s+(?P<hi>[\d.]+)\s*\)")
SPAN = re.compile(r"(`+)(.+?)\1")
WEB = re.compile(r"(?:https?|ftp)://\S+|www\.\S+|\]\([^)]*\)")     # addresses and link targets
IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)")


class Problem(Exception):
    """A check that cannot go on: the paper line (or None) and what is wrong."""

    def __init__(self, line, message):
        super().__init__(message)
        self.line, self.message = line, message


# ---------- finding and reading the paper ----------

def front_matter_title(text):
    """The title in the YAML block at the top (blank lines before it are allowed, as pandoc allows them)."""
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            return None
        m = re.match(r"title:\s*(.*?)\s*$", line)
        if m:
            value = m.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return None


def is_paper(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            head = fh.read(8192)                    # the front matter; the rest only for a matching title
            title = front_matter_title(head)
            if not (title and title.startswith(TITLE)):
                return False
            text = head + fh.read()
    except (OSError, ValueError):
        return False
    return any(line.startswith(APPENDIX_C) for line in text.split("\n"))


def candidates(repo):
    """Papers in the repository's parent folder and in the folders inside it (hidden folders are skipped)."""
    parent = Path(repo).resolve().parent
    folders = [parent]
    try:
        folders += sorted(p for p in parent.iterdir() if not p.name.startswith(".") and p.is_dir())
    except OSError:
        pass
    found = []
    for folder in folders:
        try:
            found += [p for p in sorted(folder.glob("*.md"))
                      if not p.name.startswith(".") and p.is_file() and is_paper(p)]
        except OSError:
            continue
    return found


def newest(found):
    def changed(p):
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0
    return max(found, key=lambda p: (changed(p), str(p))) if found else None


def find_paper(repo=ROOT):
    """The paper next to the repository (the most recently changed one if there are several), or None."""
    return newest(candidates(repo))


class Paper:
    """The paper as numbered lines, with its fenced code blocks and its headings found once."""

    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text(encoding="utf-8-sig").split("\n")
        self.blocks, self.headings, self.in_code = [], [], set()
        fence = block = None
        for n, line in enumerate(self.lines, 1):
            if fence:
                self.in_code.add(n)
                if re.match(r" {0,3}%s{%d,}\s*$" % (re.escape(fence[0]), len(fence)), line):
                    block["end"], fence = n, None
                else:
                    block["body"].append(line)
                continue
            m = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                block = {"line": n, "info": m.group(2).strip(), "body": [], "end": len(self.lines)}
                self.blocks.append(block)
                self.in_code.add(n)
                continue
            m = re.match(r"(#{1,6})\s+(.*?)\s*$", line)
            if m:
                self.headings.append((n, len(m.group(1))))

    def prose(self):
        """(line number, line) for every line outside fenced code."""
        return ((n, line) for n, line in enumerate(self.lines, 1) if n not in self.in_code)

    def section(self, prefix):
        """First and last line of the section whose heading line starts with prefix, or None."""
        for i, (n, level) in enumerate(self.headings):
            if self.lines[n - 1].startswith(prefix):
                end = next((m - 1 for m, deeper in self.headings[i + 1:] if deeper <= level), len(self.lines))
                return n, end
        return None

    def block(self, heading, kinds, after=None):
        """The first code block under the heading whose language is one of kinds ("" for a plain block)."""
        where = self.section(heading)
        if where is None:
            raise Problem(None, f'no heading "{heading}" in the paper')
        start = where[0]
        if after:
            start = next((n for n in range(where[0], where[1] + 1)
                          if n not in self.in_code and after in self.lines[n - 1]), where[0])
        for b in self.blocks:
            if start < b["line"] <= where[1] and (b["info"].split() or [""])[0].lower() in kinds:
                return b
        kind = "plain" if kinds == ("",) else kinds[0]
        raise Problem(where[0], f'no {kind} code block under "{heading}"' + (f' after "{after}"' if after else ""))

    def table(self, caption):
        """Header row and body rows, as (line number, cells), of the table after the caption."""
        start = next((n for n, line in self.prose() if line.startswith(caption)), None)
        if start is None:
            raise Problem(None, f'no caption "{caption}" in the paper')
        n = start + 1
        while n <= len(self.lines) and not self.lines[n - 1].strip():
            n += 1
        rows = []
        while n <= len(self.lines) and n not in self.in_code and self.lines[n - 1].lstrip().startswith("|"):
            rows.append((n, cells(self.lines[n - 1])))
            n += 1
        if len(rows) < 2 or not all(re.fullmatch(r":?-+:?", c) for c in rows[1][1]):
            raise Problem(start, f'no table with a header row after "{caption}"')
        return rows[0], rows[2:]


def cells(line):
    """The cells of one table row; an escaped \\| stays inside its cell."""
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", s)]


class Context:
    """The paper, the repository and, read once, the predictions file."""

    def __init__(self, paper, repo):
        self.paper, self.repo = paper, Path(repo)
        self._rows = self._names = None

    def predictions(self):
        if self._rows is None:
            path = self.repo / "predictions" / "predictions.csv"
            if not path.is_file():
                raise Problem(None, "predictions/predictions.csv not found in the repository")
            with open(path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
                if missing:
                    raise Problem(None, "predictions/predictions.csv has no column " + ", ".join(missing))
                self._rows = [{k: (v or "").strip() for k, v in r.items() if k} for r in reader
                              if (r.get("id") or "").strip()]
        return self._rows

    def names(self):
        """Every file and folder name in the repository, for bare names such as `human_raters.py`."""
        if self._names is None:
            self._names = set()
            for folder, dirs, files in os.walk(self.repo):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
                self._names.update(dirs)
                self._names.update(files)
        return self._names


# ---------- small helpers ----------

def clip(text, column=0, width=60):
    start = max(0, column - width // 2)
    piece = json.dumps(text[start:start + width], ensure_ascii=False)
    return ("..." if start else "") + piece + ("..." if start + width < len(text) else "")


def number(text):
    try:
        return Decimal(text.strip())
    except (InvalidOperation, AttributeError):
        return None


def to_int(text):
    t = text.lower()
    if t.isdigit():
        return int(t)
    if t in UNITS:
        return UNITS.index(t)
    tens, _, unit = t.partition("-")
    return 20 + 10 * TENS.index(tens) + (UNITS.index(unit) if unit else 0)


def plain(text):
    return " ".join(text.split())


def compare_values(pid, pairs, row):
    """Differences between paper values and the CSV row: pairs of (label, paper text, column, is a number)."""
    out = []
    for label, ours, column, numeric in pairs:
        theirs = row.get(column, "")
        if numeric:
            a, b = number(ours), number(theirs)
            if b is None:
                out.append(f"{pid}: {column} in predictions.csv is not a number ({theirs!r})")
            elif a != b:
                out.append(f"{pid}: {label} is {ours} in the paper, {theirs} in predictions.csv")
        elif plain(ours) != plain(theirs):
            out.append(f'{pid}: {label} is "{plain(ours)}" in the paper, "{theirs}" in predictions.csv')
    return out


# ---------- the checks ----------

def compare_text(block, path, label):
    """The block's lines, each ended by a newline, must equal the file byte for byte."""
    if not path.is_file():
        return [(block["line"], f"{label} not found in the repository")]
    actual = path.read_bytes()
    if "".join(line + "\n" for line in block["body"]).encode("utf-8") == actual:
        return []
    ours, text = block["body"], actual.decode("utf-8", "replace")
    theirs = text.split("\n")
    if text.endswith("\n"):
        theirs.pop()
    for i, (a, b) in enumerate(zip(ours, theirs)):
        if a != b:
            col = next((j for j, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            return [(block["line"] + 1 + i, f"differs from {label} line {i + 1}, column {col + 1}: paper {clip(a, col)}, "
                                            f"repository {clip(b, col)}")]
    if len(ours) < len(theirs):
        return [(block["end"], f"the listing stops here, but {label} goes on at line {len(ours) + 1}: "
                               f"{clip(theirs[len(ours)])}")]
    if len(ours) > len(theirs):
        return [(block["line"] + 1 + len(theirs), f"{label} ends at line {len(theirs)}, the paper goes on: "
                                                  f"{clip(ours[len(theirs)])}")]
    if not text.endswith("\n"):
        return [(block["end"], f"{label} does not end with a newline")]
    return [(block["line"], f"differs from {label} in bytes not visible here (encoding)")]


def check_listing(ctx, heading, name):
    block = ctx.paper.block(heading, ("python", "python3", "py"))
    return compare_text(block, ctx.repo / name, name)


def same(value):
    """A form in which equal JSON values are equal: key order and 9 against 9.0 do not matter; true is not 1."""
    if isinstance(value, bool) or value is None:
        return ("literal", value)
    if isinstance(value, (int, float)):
        return ("number", float(value))
    if isinstance(value, list):
        return ("list", tuple(same(x) for x in value))
    if isinstance(value, dict):
        return ("object", tuple(sorted((k, same(v)) for k, v in value.items())))
    return ("string", value)


def what_differs(ours, theirs):
    if isinstance(ours, dict) and isinstance(theirs, dict):
        for key in list(theirs) + [k for k in ours if k not in theirs]:
            if key not in ours:
                return f'field "{key}" is missing in the paper'
            if key not in theirs:
                return f'field "{key}" is not in the repository'
            if same(ours[key]) != same(theirs[key]):
                return f'"{key}" is {json.dumps(ours[key])} in the paper, {json.dumps(theirs[key])} in the repository'
    return f"paper {clip(json.dumps(ours))}, repository {clip(json.dumps(theirs))}"


def check_c4_log(ctx):
    block = ctx.paper.block("### C4.", ("json", "jsonl", "jsonlines", "ndjson"))
    path = ctx.repo / "examples" / "c4-log.jsonl"
    if not path.is_file():
        return [(block["line"], "examples/c4-log.jsonl not found in the repository")]
    ours = [(block["line"] + 1 + i, s) for i, s in enumerate(block["body"]) if s.strip()]
    theirs = [(i + 1, s) for i, s in enumerate(path.read_text(encoding="utf-8").split("\n")) if s.strip()]
    for k in range(max(len(ours), len(theirs))):
        if k >= len(ours):
            return [(block["end"], f"the log stops after {len(ours)} lines; examples/c4-log.jsonl line "
                                   f"{theirs[k][0]} is not in the paper")]
        n, mine = ours[k]
        if k >= len(theirs):
            return [(n, f"examples/c4-log.jsonl has {len(theirs)} lines; this one is not in it")]
        m, other = theirs[k]
        try:
            a = json.loads(mine)
        except ValueError as e:
            return [(n, f"not valid JSON ({getattr(e, 'msg', e)})")]
        try:
            b = json.loads(other)
        except ValueError as e:
            return [(n, f"examples/c4-log.jsonl line {m} is not valid JSON ({getattr(e, 'msg', e)})")]
        if same(a) != same(b):
            return [(n, f"differs from examples/c4-log.jsonl line {m}: {what_differs(a, b)}")]
    return []


def check_c4_output(ctx):
    block = ctx.paper.block("### C4.", ("",), after="prints the record")
    return compare_text(block, ctx.repo / "examples" / "c4-expected.txt", "examples/c4-expected.txt")


def check_ids(found, expected, caption_line, ordered):
    """The ids of a table against those of predictions.csv: missing, extra, twice and (if ordered) out of order."""
    ids = [pid for _, pid in found]
    out = []
    missing = [i for i in expected if i not in ids] if ordered else []
    extra = [(n, i) for n, i in found if i not in expected]
    twice = [(n, i) for k, (n, i) in enumerate(found) if i in ids[:k]]
    if missing:
        out.append((caption_line, "missing from the table: " + ", ".join(missing)))
    out += [(n, f"{i or 'a row without an id'} is not in predictions.csv") for n, i in extra]
    out += [(n, f"{i} appears twice") for n, i in twice]
    if ordered and not out and ids != expected:
        k = next(k for k, (a, b) in enumerate(zip(ids, expected)) if a != b)
        out.append((found[k][0], f"order differs from predictions.csv: {ids[k]} where the CSV has {expected[k]}"))
    return out


def check_table_a6(ctx):
    rows = ctx.predictions()
    by_id = {r["id"]: r for r in rows}
    (header_line, _), body = ctx.paper.table("**Table A6.**")
    problems, found = [], []
    for n, row in body:
        m = A6_ROW.match(row[0]) if row else None
        if not m:
            problems.append((n, f"first cell {clip(row[0] if row else '')} is not read as \"ID (SET)\""))
            continue
        pid = m.group("id")
        found.append((n, pid))
        if pid not in by_id:
            continue
        cell = next((c for c in (A6_CELL.search(x) for x in row[1:]) if c), None)
        if not cell:
            problems.append((n, f'{pid}: no cell reads "Check: ... Final date: ... p = ...; models ... (... to ...)"'))
            continue
        pairs = [("set", m.group("set"), "set", False), ("check date", cell.group("check"), "check_date", False),
                 ("final date", cell.group("final"), "final_date", False), ("p", cell.group("p"), "probability", True),
                 ("models", cell.group("gm"), "models_geomean_odds", True),
                 ("model range low", cell.group("lo"), "models_min", True),
                 ("model range high", cell.group("hi"), "models_max", True)]
        problems += [(n, d) for d in compare_values(pid, pairs, by_id[pid])]
        text = plain(" ".join(row))
        for column in A6_TEXT:
            wanted = plain(A6_DECLARED.get((pid, column), by_id[pid].get(column, "")))
            if wanted and wanted not in text:
                problems.append((n, f"{pid}: the {column} of predictions.csv is not in its row of Table A6"
                                    + (" (declared wording)" if (pid, column) in A6_DECLARED else "")))
    return problems + check_ids(found, [r["id"] for r in rows], header_line, ordered=True)


def check_table_4(ctx):
    rows = ctx.predictions()
    by_id = {r["id"]: r for r in rows}
    (header_line, header), body = ctx.paper.table("**Table 4.**")
    column = {name.strip().lower(): i for i, name in enumerate(header)}
    missing = [c for c in ("#", "final date", "p", "models") if c not in column]
    if missing:
        return [(header_line, "Table 4 has no column " + ", ".join(missing))]
    problems, found = [], []
    for n, row in body:
        def cell(name):
            i = column.get(name)
            return row[i] if i is not None and i < len(row) else ""
        pid = cell("#").strip("* ")
        found.append((n, pid))
        if pid not in by_id:
            continue
        r = by_id[pid]
        m = MODELS.fullmatch(cell("models").strip())
        if not m:
            problems.append((n, f'{pid}: models cell {clip(cell("models"))} is not read as "0.39 (0.25 to 0.65)"'))
            continue
        pairs = [("final date", cell("final date"), "final_date", False), ("p", cell("p"), "probability", True),
                 ("models", m.group("gm"), "models_geomean_odds", True),
                 ("model range low", m.group("lo"), "models_min", True),
                 ("model range high", m.group("hi"), "models_max", True)]
        problems += [(n, d) for d in compare_values(pid, pairs, r)]
        if "data" in column:
            data = plain(cell("data")).lower()
            if data not in DATA_SET:
                problems.append((n, f'{pid}: Data is "{data}", neither "public" nor "own study"'))
            elif DATA_SET[data] != r["set"]:
                problems.append((n, f'{pid}: Data is "{data}" in the paper, but predictions.csv puts it in Set {r["set"]}'))
    if not found:
        problems.append((header_line, "Table 4 has no rows"))
    return problems + check_ids(found, [r["id"] for r in rows], header_line, ordered=False)


def check_counts(ctx):
    rows = ctx.predictions()
    want = {"total": len(rows), "A": sum(r["set"] == "A" for r in rows), "B": sum(r["set"] == "B" for r in rows)}
    set_b = [r["id"] for r in rows if r["set"] == "B"]
    problems, seen = [], set()
    scopes = {}
    for what, pattern, kind, sections, _ in STATEMENTS:
        if sections:
            scopes[what] = [s for s in (ctx.paper.section(h) for h in sections) if s]
    for n, line in ctx.paper.prose():
        for what, pattern, kind, sections, _ in STATEMENTS:
            if sections and not any(a <= n <= b for a, b in scopes[what]):
                continue
            for m in pattern.finditer(line):
                seen.add(what)
                said = to_int(m.group(1))
                if said != want[kind]:
                    problems.append((n, f'"{m.group(0)}" says {said}, predictions.csv has {want[kind]} {KIND[kind]}'))
                if m.lastindex and m.lastindex >= 2 and m.group(2) is not None:
                    seen.add("Set B list")
                    listed = re.findall(r"[A-Za-z]+\d+[A-Za-z]*", m.group(2))
                    gone = [i for i in set_b if i not in listed]
                    extra = [i for i in listed if i not in set_b]
                    twice = sorted({i for i in listed if listed.count(i) > 1})
                    for label, ids in (("missing from the Set B list", gone), ("in the Set B list but not Set B "
                                       "in predictions.csv", extra), ("twice in the Set B list", twice)):
                        if ids:
                            problems.append((n, f"{label}: {', '.join(ids)}"))
    for what, _, _, sections, required in STATEMENTS:
        if required and what not in seen:
            where = " or ".join(f'"{h}"' for h in sections) if sections else "the paper"
            problems.append((None, f'no statement "{what}" found in {where}'))
    if "Set B list" not in seen:
        problems.append((None, 'no Set B list "Set B (N predictions: F2, ...)" found'))
    return problems


def not_a_path(word):
    return (word.startswith(("-", "~", "/", "$", "%", "\\")) or "://" in word or "@" in word
            or word.startswith("www.") or not re.search(r"[A-Za-z]", word) or re.match(r"10\.\d{4,9}/", word)
            or ".." in word.split("/"))


def exists(ctx, token):
    """A path at that place in the repository (or, for the paper's own files, beside the paper); a bare name
    anywhere in the repository."""
    path = token[2:] if token.startswith("./") else token
    folder = path.endswith("/")
    path = path.rstrip("/")
    if "/" not in token:
        return path in ctx.names()
    for base in (ctx.repo, ctx.paper.path.parent):
        hits = list(base.glob(path)) if any(c in path for c in "*?[") else [base / path]
        if any(h.is_dir() if folder else h.exists() for h in hits):
            return True
    return False


def check_repo_paths(ctx):
    problems = []
    try:
        tops = sorted(p.name for p in ctx.repo.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
    except OSError:
        tops = []
    in_text = re.compile(r"(?<![\w./@:~-])((?:%s)/[\w./*-]*)" % "|".join(map(re.escape, tops))) if tops else None
    for n, line in ctx.paper.prose():
        for span in SPAN.finditer(line):
            words = [w.strip("\"'()[]{}<>,;:") for w in span.group(2).split()]
            words = [w for w in words if w]
            for w in words:
                if not_a_path(w) or not ("/" in w or w.lower().endswith(EXTENSIONS)):
                    continue
                if len(words) > 1 and "/" not in w and not w.lower().endswith(SCRIPTS):
                    continue        # a data file given to a command: the reader's own file
                if not exists(ctx, w):
                    problems.append((n, f"`{w}` is not in the repository"))
        if in_text:
            for m in in_text.finditer(WEB.sub(" ", SPAN.sub(" ", line))):
                token = m.group(1).rstrip(".,;:")
                if (token.endswith("/") or "." in token.rsplit("/", 1)[-1]) and not exists(ctx, token):
                    problems.append((n, f"{token} (in the text) is not in the repository"))
    return problems


def check_figures(ctx):
    problems = []
    for n, line in ctx.paper.prose():
        for m in IMAGE.finditer(line):
            target = m.group(1)
            if "://" in target or target.startswith("data:"):
                continue
            path = ctx.paper.path.parent / unquote(target)
            svg = path.with_suffix(".svg")
            if not path.is_file():
                problems.append((n, f"{target} is not beside the paper"))
            if svg != path and not svg.is_file():
                problems.append((n, f"{target} has no {svg.name} beside it"))
    return problems


CHECKS = [
    ("listing-horizon", lambda ctx: check_listing(ctx, "### C2.", "horizon.py")),
    ("listing-brier", lambda ctx: check_listing(ctx, "### C3.", "brier.py")),
    ("c4-log", check_c4_log),
    ("c4-output", check_c4_output),
    ("table-a6", check_table_a6),
    ("table-4", check_table_4),
    ("counts", check_counts),
    ("repo-paths", check_repo_paths),
    ("figures", check_figures),
]


def run_checks(paper, repo):
    """[(name, [(line or None, message), ...])], one entry per check; an empty list means OK."""
    ctx = Context(paper, repo)
    results = []
    for name, check in CHECKS:
        try:
            problems = check(ctx)
        except Problem as p:
            problems = [(p.line, p.message)]
        except Exception as e:  # a check must report, never stop the others
            problems = [(None, f"could not run ({type(e).__name__}: {e})")]
        results.append((name, problems))
    return results


def line_text(name, problems):
    if not problems:
        return f"OK {name}"
    parts = [f"line {n}: {msg}" if n else msg for n, msg in problems]
    if len(parts) > SHOWN:
        parts = parts[:SHOWN] + [f"and {len(parts) - SHOWN} more (--json lists them all)"]
    return f"FAIL {name}: " + "; ".join(parts)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Check that the paper and this repository say the same thing: the listings of Appendix C, "
                    "the worked example, Tables 4 and A6, the counts of predictions, the files and the figures "
                    "the paper names.",
        epilog="Exit code 0 when every check passes, 1 when one fails, 2 when no paper is found "
               "(0 with --if-present).")
    ap.add_argument("--paper", help="the paper, a Markdown file (default: found next to the repository)")
    ap.add_argument("--repo", default=str(ROOT), help="the repository (default: the folder above tools/)")
    ap.add_argument("--json", action="store_true", help="print the results as a JSON list")
    ap.add_argument("--if-present", action="store_true", help="exit 0 when no paper is found (for scripts)")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    if not repo.is_dir():
        print(f"no repository at {repo}", file=sys.stderr)
        return 2
    found = [] if args.paper else candidates(repo)
    path = Path(args.paper) if args.paper else newest(found)
    if path is None or not path.is_file():
        where = f"at {path}" if path is not None else (
            f'next to {repo.resolve()} (a Markdown file titled "{TITLE}..." with "{APPENDIX_C}"); '
            "give its path with --paper")
        print("[]" if args.json else f"no paper found {where}")
        if args.json:
            print(f"no paper found {where}", file=sys.stderr)
        return 0 if args.if_present else 2
    if len(found) > 1:
        print(f"note: {len(found)} papers found; checking the newest, {path} (choose with --paper)", file=sys.stderr)
    try:
        paper = Paper(path)
    except (OSError, ValueError) as e:
        print(f"cannot read {path} as UTF-8 text: {e}", file=sys.stderr)
        return 2
    results = run_checks(paper, repo)
    if args.json:
        print(json.dumps([{"name": name, "ok": not problems,
                           "problems": [{"line": n, "message": msg} for n, msg in problems]}
                          for name, problems in results], indent=2, ensure_ascii=False))
    else:
        print(f"paper: {path}")
        for name, problems in results:
            print(line_text(name, problems))
    return 1 if any(problems for _, problems in results) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
