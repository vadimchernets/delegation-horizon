#!/usr/bin/env python3
"""table_g2.py: Table G2 of the paper (agreement of professionals on reference hours), from the Prolific long CSV.

Teaches: how a registered analysis becomes a published table without a number typed by hand. Every agreement
figure comes from the functions of human_raters.py, the script filed on OSF before data (10.17605/OSF.IO/V92R8),
imported and called unchanged, in the order its main() calls them; tests/test_pilot.py checks that this table and
that script's printout agree. Beside them it counts who was excluded and why, and puts the four model raters of
Appendix E on the same ten tasks of each domain (the "56%" of Appendix G2 is their pooled share on the 20 tasks).
Limits: it prints what the registered rules give; the screening comparison, which was not registered, is
screen_compare.py.
Usage: python3 pilot/table_g2.py ratings-long.csv [--bank pilot/task-bank-v0.csv]
       [--models pilot/results/model-ratings.csv] [--format md|csv]
Licence: MIT
"""
import argparse
import csv
import itertools
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import human_raters as hr  # noqa: E402  (registered on OSF; imported, never edited)

COLUMNS = ("domain", "rater", "task_id", "reference_hours", "attention_ok", "competency_ok")


def check_file(path):
    """The registered script reads the file as plain UTF-8 with commas; say so before it stops on anything else."""
    try:
        with open(path, "rb") as fh:
            first = fh.readline()
    except OSError as err:
        sys.exit(f"{path}: {err.strerror}")
    if first.startswith(b"\xef\xbb\xbf"):
        sys.exit(f"{path}: the file starts with a byte order mark; save it as CSV UTF-8 without one, as "
                 "prolific_to_long.py writes it")
    head = [h.strip() for h in first.decode("utf-8", "replace").strip().split(",")]
    missing = [c for c in COLUMNS if c not in head]
    if missing:
        sys.exit(f"{path}: the header lacks {', '.join(missing)}; the file must be the comma-separated long CSV that "
                 "prolific_to_long.py writes")


def who_was_excluded(path):
    """Per domain: participants admitted, failed the attention check, failed the competency question only."""
    flags = defaultdict(dict)
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ok = flags[r["domain"]].setdefault(r["rater"], [True, True])
            ok[0] = ok[0] and r["attention_ok"].strip() == "1"
            ok[1] = ok[1] and r["competency_ok"].strip() == "1"
    return {d: (len(f), sum(not a for a, _ in f.values()), sum(a and not c for a, c in f.values()))
            for d, f in flags.items()}


def model_share(models_path, prefix):
    """Pooled share of model-rater pairs within x1.5 on the tasks whose id starts with prefix."""
    by_task = defaultdict(dict)
    with open(models_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["task_id"].startswith(prefix):
                by_task[r["task_id"]][r["rater"]] = float(r["reference_hours"])
    pairs = [(a, b) for v in by_task.values() for a, b in itertools.combinations(v.values(), 2)]
    return sum(max(a, b) / min(a, b) <= 1.5 for a, b in pairs), len(pairs)


def domain_rows(path, bank_path=None, models_path=None):
    """One dict per domain, computed exactly as human_raters.main() computes its printout."""
    check_file(path)
    rows, _ = hr.load(path)
    bank = {}
    if bank_path:
        with open(bank_path, encoding="utf-8") as fh:
            bank = {r["task_id"]: r.get("target_rung", "") for r in csv.DictReader(fh)}
    admitted = who_was_excluded(path)
    out = []
    for domain in sorted(set(admitted) | {d for d, *_ in rows}):     # a domain with nobody kept keeps its row
        main_tasks, retest = defaultdict(dict), defaultdict(dict)
        for d, who, task, h in rows:
            if d != domain:
                continue
            (retest if task.endswith("-retest") else main_tasks)[task.replace("-retest", "")][who] = h
        raters = {w for r in main_tasks.values() for w in r}
        share, pairs = hr.pair_share(main_tasks)
        cshare, _ = hr.pair_share(hr.calibrated(main_tasks))
        tasks = sorted(main_tasks)
        complete = [w for w in sorted(raters) if all(w in main_tasks[t] for t in tasks)]
        try:
            icc = hr.icc21([[math.log(main_tasks[t][w]) for w in complete] for t in tasks]) if len(complete) > 1 else float("nan")
        except ZeroDivisionError:                  # every estimate the same: the registered formula has no value
            icc = float("nan")
        rt = [(main_tasks[t][w], h) for t, r in retest.items() for w, h in r.items() if w in main_tasks[t]]
        rt_share = sum(max(a, b) / min(a, b) <= 1.5 for a, b in rt) / len(rt) if rt else float("nan")
        medians = {t: statistics.median(main_tasks[t].values()) for t in tasks}
        on_rung = sum(hr.rung(medians[t]) == bank.get(t) for t in tasks)
        n, att, comp = admitted.get(domain, (len(raters), 0, 0))
        prefix = tasks[0][:2] if tasks else ""
        model = model_share(models_path, prefix) if models_path and prefix else (0, 0)
        out.append({"domain": domain, "admitted": n, "failed_attention": att, "failed_competency": comp,
                    "kept": len(raters), "pairs": pairs, "share": share, "calibrated": cshare,
                    "icc": icc, "complete": len(complete), "retest": rt_share, "retest_n": len(rt),
                    "on_rung": on_rung, "tasks": len(tasks), "model_hits": model[0], "model_pairs": model[1],
                    "threshold_met": share >= hr.THRESHOLD})
    return out


def fmt(x, digits=2):
    return "n/a" if isinstance(x, float) and math.isnan(x) else f"{x:.{digits}f}"


def markdown(rows):
    head = ("| Domain | Admitted | Excluded: attention, competency | Kept | Rater pairs | Pairs within ×1.5 "
            f"(threshold {hr.THRESHOLD:.2f}) | Same, each rater's level removed | ICC(2,1), log hours "
            "| Retest within ×1.5 | Task medians on the intended rung | Model raters, pairs within ×1.5 |")
    lines = [head, "|" + "---|" * 11]
    for r in rows:
        model = (f"{r['model_hits'] / r['model_pairs']:.0%} ({r['model_hits']} of {r['model_pairs']})"
                 if r["model_pairs"] else "n/a")
        lines.append(f"| {r['domain']} | {r['admitted']} | {r['failed_attention']}, {r['failed_competency']} "
                     f"| {r['kept']} | {r['pairs']} | {fmt(r['share'], 3)} ({'met' if r['threshold_met'] else 'not met'}) "
                     f"| {fmt(r['calibrated'])} | {fmt(r['icc'])} ({r['complete']} raters) "
                     f"| {fmt(r['retest'])} (n = {r['retest_n']}) | {r['on_rung']} of {r['tasks']} | {model} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Table G2 from the Prolific long CSV, with the registered functions.")
    ap.add_argument("ratings", help="long CSV written by prolific_to_long.py")
    ap.add_argument("--bank", default=str(HERE / "task-bank-v0.csv"))
    ap.add_argument("--models", default=str(HERE / "results" / "model-ratings.csv"))
    ap.add_argument("--format", choices=["md", "csv"], default="md")
    args = ap.parse_args(argv)
    rows = domain_rows(args.ratings, args.bank, args.models)
    if args.format == "csv":
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]) if rows else ["domain"])
        w.writeheader()
        w.writerows(rows)
        return
    sys.stdout.write(markdown(rows))
    hits = sum(r["model_hits"] for r in rows)
    pairs = sum(r["model_pairs"] for r in rows)
    if pairs:
        print(f"\nModel raters of Appendix E on the same tasks, pooled: {hits} of {pairs} pairs within ×1.5 "
              f"({hits / pairs:.0%}).")


if __name__ == "__main__":
    main()
