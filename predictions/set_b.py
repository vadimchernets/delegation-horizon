#!/usr/bin/env python3
"""set_b.py: apply the frozen came-true and did-not rules of the interval-based Set B predictions to a study's estimates.

Teaches: Section 11.2 and Appendix D. Set B resolves only from studies registered separately, and nine of its rules
are written on a confidence interval (F2, F3, F3b, F4a, F4b, F7, F12, F26, F34): came true and did not each need the
interval on the right side of a frozen threshold, and an interval that meets neither rule is unresolved, never a
success (F12 has no unresolved interval: its did-not rule is "otherwise"). The subcommand verdict applies these rules
and prints the frozen words beside each verdict, read from predictions.csv; only the numbers are written here. The
subcommands diff and or give the intervals the rules are written on when the data are counts: a difference of two
shares with the hybrid score interval of Newcombe (1998, method 10), and the Mantel-Haenszel odds ratio over strata
with the interval of Robins, Breslow and Greenland (1986), for F7. The sample size behind these studies (1,500
people per group: about 0.8 power for a true advantage of 5 points, two-sided alpha 0.05) is tools/power.py. On a
tie the words decide: a bound exactly on a threshold is not "above", "below", "beyond" or "wholly outside" it, but
it is "within" or "inside" a margin (F7, F26) and "0.75 or above" (F34); a callback gap of exactly 3 points is not
"less than 3".
Limits: it applies the frozen rules to estimates a registered study produced; it does not fit the study's model.
The diff subcommand assumes two independent groups and gives an unadjusted interval: a clustered, paired (an audit
that sends both portfolios to one posting) or covariate-adjusted analysis needs the interval its protocol names,
given to verdict. The or subcommand stratifies on categories; if F7's protocol fits a logistic model, its 90%
interval goes to verdict. F14, F18, F19, F20 and F35 have no interval rule and are not applied here, and "no
comparable data by the final date" is recorded by people. Give bounds unrounded.
Usage:
  python3 predictions/set_b.py verdict estimates.csv       (columns id,estimate,lower,upper and, for F7, level)
  python3 predictions/set_b.py verdict --id F2 --estimate -4.2 --lower -7.5 --upper -0.9
  python3 predictions/set_b.py verdict --id F7 --day 1.02 0.84 1.24 --week-up 0.97 0.71 1.33
  python3 predictions/set_b.py diff 56 70 48 80 [--conf 0.95] [--id F3]
  python3 predictions/set_b.py or strata.csv [--exposed 1] [--conf 0.90] [--id F7]    (stratum,group,passed,n[,level])
Licence: MIT
"""
import argparse
import csv
import hashlib
import math
import os
import sys
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "predictions.csv")
MANIFEST = os.path.join(HERE, "registered-SHA256.txt")
REGISTERED = "frozen, registered on OSF on 9 October 2026, doi:10.17605/OSF.IO/VW6P9"

CAME, DID_NOT, UNRESOLVED = "came true", "did not", "unresolved"
STATUS = {CAME: "came_true", DID_NOT: "did_not", UNRESOLVED: "unresolved"}      # the codes score.py reads
POINTS, ODDS_RATIO, ICC = "points", "odds ratio", "ICC"

# Only the numbers of the frozen rules are written here. Their words are read from predictions.csv when the script
# runs, and tests/test_set_b.py checks that every number below is the one the frozen words state.
RULES = {
    "F2": {"kind": "lower_above", "scale": POINTS, "level": 0.95, "cut": -10.0},
    "F3": {"kind": "lower_above", "scale": POINTS, "level": 0.95, "cut": 0.0},
    "F3b": {"kind": "lower_above", "scale": POINTS, "level": 0.95, "cut": 0.0},
    "F4a": {"kind": "upper_below", "scale": POINTS, "level": 0.95, "cut": 10.0},
    "F4b": {"kind": "upper_below", "scale": POINTS, "level": 0.95, "cut": 10.0},
    "F7": {"kind": "equivalence", "scale": ODDS_RATIO, "level": 0.90, "low": 0.67, "high": 1.5},
    "F12": {"kind": "lower_above_or_did_not", "scale": POINTS, "level": 0.95, "cut": 0.0},
    "F26": {"kind": "callback", "scale": POINTS, "level": 0.95, "gap": 3.0, "margin": 5.0},
    "F34": {"kind": "lower_at_least", "scale": ICC, "level": 0.95, "cut": 0.75},
}
NOT_INTERVAL = ("F14", "F18", "F19", "F20", "F35")        # Set B without an interval rule: read their frozen text
F7_LEVELS = (("day", "Day"), ("week_up", "Week and above"))


# ---- numbers and checks ------------------------------------------------------------------------------------------

def number(x, what):
    """A finite float, or a ValueError naming what was expected."""
    try:
        value = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"{what} must be a number, not {x!r}") from None
    if not math.isfinite(value):
        raise ValueError(f"{what} must be a finite number, not {x!r}")
    return value


def whole(x, what, least=0):
    """A whole number of at least `least` (56 and 56.0 are both taken), or a ValueError."""
    if isinstance(x, int) and not isinstance(x, bool):
        value = x
    else:
        try:
            f = float(x)
        except (TypeError, ValueError):
            f = math.nan
        if not (math.isfinite(f) and f.is_integer()):
            raise ValueError(f"{what} must be a whole number, not {x!r}")
        value = int(f)
    if value < least:
        raise ValueError(f"{what} must be {least} or more, not {value}")
    return value


def z_for(conf):
    """The normal quantile of a two-sided interval at confidence level conf."""
    conf = number(conf, "the confidence level")
    if not 0 < conf < 1:
        raise ValueError(f"the confidence level must lie between 0 and 1 (for example 0.95), not {conf:g}")
    return NormalDist().inv_cdf((1 + conf) / 2)


def rule_id(pid):
    """The id as the frozen table spells it, or a ValueError saying why set_b.py does not apply it."""
    text = str(pid or "").strip()
    for known in tuple(RULES) + NOT_INTERVAL:
        if known.lower() == text.lower():
            if known in NOT_INTERVAL:
                raise ValueError(f"{known}: a Set B prediction without an interval rule; read its frozen text "
                                 f"(set_b.py applies {', '.join(RULES)})")
            return known
    raise ValueError(f"{text or '(no id)'}: not one of the interval rules of Set B ({', '.join(RULES)})")


def check_interval(pid, est, lo, hi):
    """The estimate and its bounds as floats, after the checks every interval must pass."""
    est = number(est, f"{pid}: the estimate")
    lo = number(lo, f"{pid}: the lower bound")
    hi = number(hi, f"{pid}: the upper bound")
    if lo > hi:
        raise ValueError(f"{pid}: the lower bound {lo:g} lies above the upper bound {hi:g}")
    if not lo <= est <= hi:
        raise ValueError(f"{pid}: the estimate {est:g} lies outside its interval {lo:g} to {hi:g}; check the columns")
    scale = RULES[pid]["scale"]
    if scale == POINTS and (lo < -100 or hi > 100):
        raise ValueError(f"{pid}: a difference of two shares lies within -100 to 100 points, not {lo:g} to {hi:g}")
    if scale == ODDS_RATIO and lo <= 0:
        raise ValueError(f"{pid}: an odds ratio and its bounds lie above zero, not {lo:g}")
    if scale == ICC and hi > 1:
        raise ValueError(f"{pid}: an ICC cannot exceed 1, not {hi:g}")
    return est, lo, hi


def shown(pid, x):
    return f"{x:+.2f}" if RULES[pid]["scale"] == POINTS else f"{x:.3f}"


# ---- the frozen rules ----------------------------------------------------------------------------------------------

def judge(pid, est, lo, hi):
    """(verdict, reason) for one estimate and its interval under the frozen rule of pid; F7 goes to judge_f7."""
    pid = rule_id(pid)
    if pid == "F7":
        raise ValueError("F7: two intervals are needed, at Day and at Week and above")
    est, lo, hi = check_interval(pid, est, lo, hi)
    rule = RULES[pid]
    kind = rule["kind"]

    def s(x):
        return shown(pid, x)
    if kind == "lower_above":                                     # F2, F3, F3b
        cut = rule["cut"]
        if lo > cut:
            return CAME, f"the lower bound {s(lo)} lies above {cut:g}"
        if hi < cut:
            return DID_NOT, f"the upper bound {s(hi)} lies below {cut:g}"
        return UNRESOLVED, f"the interval {s(lo)} to {s(hi)} includes {cut:g}, so it meets neither rule"
    if kind == "upper_below":                                     # F4a, F4b
        cut = rule["cut"]
        if hi < cut:
            return CAME, f"the upper bound {s(hi)} lies below {cut:g}"
        if lo > cut:
            return DID_NOT, f"the lower bound {s(lo)} lies above {cut:g}"
        return UNRESOLVED, f"the interval {s(lo)} to {s(hi)} includes {cut:g}, so it meets neither rule"
    if kind == "lower_above_or_did_not":                          # F12
        cut = rule["cut"]
        if lo > cut:
            return CAME, f"the lower bound {s(lo)} lies above {cut:g}, so the interval excludes zero on the higher side"
        return DID_NOT, (f"the lower bound {s(lo)} is not above {cut:g}, so the came-true rule is not met "
                         "(an interval never leaves F12 unresolved)")
    if kind == "callback":                                        # F26
        gap, margin = rule["gap"], rule["margin"]
        small, inside = abs(est) < gap, -margin <= lo and hi <= margin
        if small and inside:
            return CAME, (f"the estimate {s(est)} is less than {gap:g} points from zero and the interval "
                          f"{s(lo)} to {s(hi)} lies inside plus or minus {margin:g}")
        if lo > gap or hi < -gap:
            return DID_NOT, f"the interval {s(lo)} to {s(hi)} lies wholly beyond {gap:g} points"
        why = []
        if not small:
            why.append(f"the estimate {s(est)} is not less than {gap:g} points from zero")
        if not inside:
            why.append(f"the interval {s(lo)} to {s(hi)} reaches beyond plus or minus {margin:g}")
        return UNRESOLVED, (" and ".join(why) + f", and the interval does not lie wholly beyond {gap:g} points, "
                            "so it meets neither rule")
    if kind == "lower_at_least":                                  # F34
        cut = rule["cut"]
        if lo >= cut:
            return CAME, f"the lower bound {s(lo)} is {cut:g} or above"
        if hi < cut:
            return DID_NOT, f"the upper bound {s(hi)} lies below {cut:g}"
        return UNRESOLVED, (f"the lower bound {s(lo)} lies below {cut:g} and the upper bound {s(hi)} does not, "
                            "so it meets neither rule")
    raise ValueError(f"{pid}: no rule of kind {kind}")


def judge_f7(day, week_up):
    """(verdict, reason) for F7 from (estimate, lower, upper) of the odds ratio at Day and at Week and above."""
    low, high = RULES["F7"]["low"], RULES["F7"]["high"]
    margin = f"{low:g} to {high:g}"
    within, outside = [], []
    for (_, name), values in zip(F7_LEVELS, (day, week_up)):
        if values is None or len(values) != 3:
            raise ValueError(f"F7: give the estimate, the lower and the upper bound at {name}")
        _, lo, hi = check_interval("F7", *values)
        if low <= lo and hi <= high:
            within.append(name)
        elif hi < low or lo > high:
            outside.append(name)
    if outside:
        return DID_NOT, f"the interval lies wholly outside {margin} at {' and at '.join(outside)}"
    if len(within) == 2:
        return CAME, f"the interval lies within {margin} at both levels"
    if within:
        return UNRESOLVED, f"the interval lies within {margin} at {within[0]} only"
    return UNRESOLVED, f"the interval lies neither within nor wholly outside {margin} at either level"


# ---- the intervals the rules rest on --------------------------------------------------------------------------

def counts(x, n, what):
    """x of n as whole numbers with 0 <= x <= n and n >= 1."""
    x, n = whole(x, f"{what}: the count"), whole(n, f"{what}: the total", 1)
    if x > n:
        raise ValueError(f"{what}: {x} of {n} is not a count (it needs 0 <= x <= n)")
    return x, n


def wilson(x, n, z):
    """The Wilson score interval of x of n, without continuity correction."""
    p, zz = x / n, z * z
    centre = (p + zz / (2 * n)) / (1 + zz / n)
    half = z * math.sqrt(p * (1 - p) / n + zz / (4 * n * n)) / (1 + zz / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe(x1, n1, x2, n2, conf=0.95):
    """x1/n1 minus x2/n2 with the hybrid score interval of Newcombe (1998), method 10, as shares (not points)."""
    x1, n1 = counts(x1, n1, "group 1")
    x2, n2 = counts(x2, n2, "group 2")
    z = z_for(conf)
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1, z)
    l2, u2 = wilson(x2, n2, z)
    d = (x1 * n2 - x2 * n1) / (n1 * n2)
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def points(x1, n1, x2, n2):
    """x1/n1 minus x2/n2 in percentage points, rounded once, so that a gap of exactly 3 points stays 3."""
    return 100 * (x1 * n2 - x2 * n1) / (n1 * n2)


def mantel_haenszel(tables, conf=0.90):
    """Mantel-Haenszel odds ratio over strata with the Robins-Breslow-Greenland (1986) interval.

    tables: one (a, b, c, d) per stratum, where a and b passed and did not pass in the exposed group (for F7, the
    people with IT education) and c and d the same in the other group."""
    z = z_for(conf)
    sr = ss = spr = spsqr = sqs = 0.0
    for table in tables:
        a, b, c, d = (whole(v, "a cell of a stratum") for v in table)
        n = a + b + c + d
        if n == 0:
            continue
        r, s, p, q = a * d / n, b * c / n, (a + d) / n, (b + c) / n
        sr, ss = sr + r, ss + s
        spr, spsqr, sqs = spr + p * r, spsqr + p * s + q * r, sqs + q * s
    if sr == 0 or ss == 0:
        raise ValueError("the Mantel-Haenszel odds ratio is zero or infinite here (ad = 0 in every stratum, or "
                         "bc = 0 in every stratum), so no interval can be given")
    est = sr / ss
    half = z * math.sqrt(spr / (2 * sr * sr) + spsqr / (2 * sr * ss) + sqs / (2 * ss * ss))
    return est, est * math.exp(-half), est * math.exp(half)


# ---- files ----------------------------------------------------------------------------------------------------------

def read_table(path):
    """The frozen table as {id: row}."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    need = ("id", "set", "came_true_if", "did_not_come_true_if", "unresolved_if")
    if not rows or any(c not in rows[0] for c in need):
        raise ValueError(f"{path}: not the prediction table (it needs the columns {', '.join(need)})")
    return {(r["id"] or "").strip(): r for r in rows}


def table_note(path):
    """One line saying whether the rule texts come from the table registered on 9 October 2026."""
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    registered = None
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 2 and parts[1] == "predictions.csv":
                    registered = parts[0]
    except OSError:
        return f"rule texts from {path} (registered-SHA256.txt not found, so not checked)"
    if digest == registered:
        return f"prediction table: {REGISTERED} (SHA-256 as registered)"
    return (f"WARNING: {path} is not the registered table (its SHA-256 differs from registered-SHA256.txt), "
            "so the rule texts below may not be the frozen ones")


def table_id(pid, table):
    """The id checked against the frozen table first, then against the rules set_b.py applies."""
    text = str(pid or "").strip()
    found = [k for k in table if k.lower() == text.lower()]
    if not found:
        raise ValueError(f"{text or '(no id)'}: not in the frozen table")
    if (table[found[0]].get("set") or "").strip() == "A":
        raise ValueError(f"{found[0]}: a Set A prediction; it resolves from public data and predictions/resolve/, "
                         "not from a study")
    return rule_id(found[0])


def csv_rows(path, need):
    """(line number, row) for each non-blank row, with lower-case column names, after checking the columns."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in need if c not in header]
        if missing:
            raise ValueError(f"{path}: missing column {', '.join(missing)} (found: {', '.join(header) or 'nothing'}); "
                             f"a comma-separated file with the columns {','.join(need)} is expected")
        out = []
        for raw in reader:
            row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
            if any(row.values()):
                out.append((reader.line_num, row))
    if not out:
        raise ValueError(f"{path}: no rows")
    return out, "level" in header


def read_estimates(path, table):
    """{id: (estimate, lower, upper)}, and for F7 {level: (estimate, lower, upper)}, from a CSV."""
    items = {}
    rows, _ = csv_rows(path, ("id", "estimate", "lower", "upper"))
    for line, row in rows:
        try:
            pid = table_id(row["id"], table)
            values = check_interval(pid, row["estimate"], row["lower"], row["upper"])
            level = row.get("level", "").lower()
            if pid == "F7":
                if level not in dict(F7_LEVELS):
                    raise ValueError(f"F7: level must be day or week_up, not {level!r}")
                slot = items.setdefault("F7", {})
                if level in slot:
                    raise ValueError(f"F7: level {level} listed twice")
                slot[level] = values
            else:
                if level:
                    raise ValueError(f"{pid}: the level column is for F7 only")
                if pid in items:
                    raise ValueError(f"{pid}: listed twice")
                items[pid] = values
        except ValueError as e:
            raise ValueError(f"{path}, line {line}: {e}") from None
    if "F7" in items and len(items["F7"]) != 2:
        raise ValueError("F7 needs two rows, one with level day and one with level week_up")
    return items


def estimates_from_args(args, table):
    if not args.id:
        raise ValueError("give a CSV of estimates, or --id with --estimate, --lower and --upper "
                         "(for F7, --day and --week-up)")
    pid = table_id(args.id, table)
    if pid == "F7":
        if any(v is not None for v in (args.estimate, args.lower, args.upper)):
            raise ValueError("F7 takes --day and --week-up, three numbers each: estimate, lower, upper")
        if args.day is None or args.week_up is None:
            raise ValueError("F7 needs both --day and --week-up, three numbers each: estimate, lower, upper")
        return {"F7": {"day": check_interval("F7", *args.day), "week_up": check_interval("F7", *args.week_up)}}
    if args.day is not None or args.week_up is not None:
        raise ValueError(f"--day and --week-up are for F7; {pid} takes --estimate, --lower and --upper")
    if None in (args.estimate, args.lower, args.upper):
        raise ValueError(f"{pid} needs --estimate, --lower and --upper")
    return {pid: check_interval(pid, args.estimate, args.lower, args.upper)}


def read_strata(path, exposed):
    """({level: [(a, b, c, d), one per stratum]}, the other group, notes) from a CSV of stratum,group,passed,n."""
    exposed = str(exposed).strip()
    cells, groups = {}, []
    rows, has_level = csv_rows(path, ("stratum", "group", "passed", "n"))
    for line, row in rows:
        try:
            level, stratum, group = row.get("level", "").lower(), row["stratum"], row["group"]
            if has_level and not level:
                raise ValueError("the level is empty")
            if not group:
                raise ValueError("the group is empty")
            passed, n = counts(row["passed"], row["n"], f"stratum {stratum}, group {group}")
            by_group = cells.setdefault((level, stratum), {})
            if group in by_group:
                raise ValueError(f"stratum {stratum}, group {group} listed twice")
            by_group[group] = (passed, n)
            if group not in groups:
                groups.append(group)
        except ValueError as e:
            raise ValueError(f"{path}, line {line}: {e}") from None
    if len(groups) != 2:
        raise ValueError(f"the group column needs exactly two values, one of them {exposed} "
                         f"(found: {', '.join(groups)})")
    if exposed not in groups:
        raise ValueError(f"no rows with group {exposed}: name the exposed group (for F7, IT education) with "
                         f"--exposed (groups found: {', '.join(groups)})")
    other = groups[1] if groups[0] == exposed else groups[0]
    strata, notes = {}, []
    for (level, stratum), by_group in cells.items():
        tables = strata.setdefault(level, [])
        if len(by_group) < 2:
            notes.append(f"note: stratum {stratum}{' at ' + level if level else ''} has one group only and carries "
                         "no information; skipped")
            continue
        (a, n1), (c, n0) = by_group[exposed], by_group[other]
        tables.append((a, n1 - a, c, n0 - c))
    return strata, other, notes


# ---- subcommands ----------------------------------------------------------------------------------------------------

def describe(pid, est, lo, hi, where=""):
    rule = RULES[pid]
    what = {POINTS: "estimate", ODDS_RATIO: "odds ratio", ICC: "ICC"}[rule["scale"]]
    unit = " points" if rule["scale"] == POINTS else ""
    return (f"{pid}{where}: {what} {shown(pid, est)}{unit}, interval {shown(pid, lo)} to {shown(pid, hi)} "
            f"(the rule reads the {rule['level'] * 100:g}% interval)")


def show(pid, lines, verdict, why, table):
    row = table[pid]
    for line in lines:
        print(line)
    print(f"  verdict: {verdict} (status {STATUS[verdict]} in an outcomes file)")
    print(f"  because: {why}")
    print(f"  came true if (frozen): {row['came_true_if']}")
    print(f"  did not if (frozen): {row['did_not_come_true_if']}")
    print(f"  unresolved if (frozen): {row['unresolved_if']}")


def level_for(pid, conf, default):
    """The confidence level to compute: the one the rule of pid reads, or the default when no id is given."""
    if pid is None:
        return default if conf is None else conf
    need = RULES[pid]["level"]
    if conf is not None and not abs(conf - need) <= 1e-9:
        raise ValueError(f"{pid} is judged on the {need * 100:g}% interval; drop --conf or set it to {need:g}")
    return need


def cmd_verdict(args):
    table = read_table(args.predictions)
    given = (args.id, args.estimate, args.lower, args.upper, args.day, args.week_up)
    if args.csv and any(v is not None for v in given):
        raise ValueError("give a CSV of estimates or --id with its numbers, not both")
    items = read_estimates(args.csv, table) if args.csv else estimates_from_args(args, table)
    results = []
    for pid in table:                                             # the order of the frozen table
        if pid == "F7" and pid in items:
            verdict, why = judge_f7(items[pid]["day"], items[pid]["week_up"])
            lines = [describe(pid, *items[pid][key], where=" at " + name) for key, name in F7_LEVELS]
        elif pid in items:
            verdict, why = judge(pid, *items[pid])
            lines = [describe(pid, *items[pid])]
        else:
            continue
        results.append((pid, lines, verdict, why))
    print(table_note(args.predictions))
    for pid, lines, verdict, why in results:
        show(pid, lines, verdict, why, table)
    tally = [sum(1 for r in results if r[2] == v) for v in (CAME, DID_NOT, UNRESOLVED)]
    print("came true: {}, did not: {}, unresolved: {}".format(*tally))


def cmd_diff(args):
    pid = table = None
    if args.id:
        table = read_table(args.predictions)
        pid = table_id(args.id, table)
        if pid == "F7":
            raise ValueError("F7 is an odds ratio at two levels: use the or subcommand")
        if RULES[pid]["scale"] != POINTS:
            raise ValueError(f"{pid} is not a difference of two shares: give the study's interval to verdict")
    conf = level_for(pid, args.conf, 0.95)
    _, lo, hi = newcombe(args.x1, args.n1, args.x2, args.n2, conf)
    est, lo, hi = points(args.x1, args.n1, args.x2, args.n2), 100 * lo, 100 * hi
    print(f"group 1: {args.x1} of {args.n1} ({100 * args.x1 / args.n1:.2f}%); "
          f"group 2: {args.x2} of {args.n2} ({100 * args.x2 / args.n2:.2f}%)")
    print(f"difference, group 1 minus group 2: {est:+.2f} points; {conf * 100:g}% Newcombe hybrid score interval "
          f"(method 10): {lo:+.2f} to {hi:+.2f}")
    if pid:
        verdict, why = judge(pid, est, lo, hi)
        print(table_note(args.predictions))
        show(pid, [describe(pid, est, lo, hi)], verdict, why, table)


def cmd_or(args):
    pid = table = None
    if args.id:
        table = read_table(args.predictions)
        pid = table_id(args.id, table)
        if pid != "F7":
            raise ValueError(f"{pid} is not an odds ratio: or applies only to F7 (use diff or verdict)")
    conf = level_for(pid, args.conf, RULES["F7"]["level"])
    strata, other, notes = read_strata(args.csv, args.exposed)
    if pid == "F7" and set(strata) != set(dict(F7_LEVELS)):
        raise ValueError("F7 needs a level column with the values day and week_up (found: "
                         + (", ".join(sorted(k for k in strata if k)) or "no level column") + ")")
    results, lines = {}, []
    for level, tables in strata.items():
        if not tables:
            raise ValueError(f"{'at ' + level + ', ' if level else ''}no stratum has both groups")
        est, lo, hi = mantel_haenszel(tables, conf)
        results[level] = (est, lo, hi)
        lines.append(f"  {'at ' + level + ', ' if level else ''}{len(tables)} strata: {est:.3f}, "
                     f"interval {lo:.3f} to {hi:.3f}")
    verdict = judge_f7(results["day"], results["week_up"]) if pid else None
    for note in notes:
        print(note)
    print(f"Mantel-Haenszel odds ratio of passing, group {args.exposed} against group {other}, with the "
          f"{conf * 100:g}% Robins-Breslow-Greenland interval:")
    print("\n".join(lines))
    if pid:
        print(table_note(args.predictions))
        show("F7", [describe("F7", *results[key], where=" at " + name) for key, name in F7_LEVELS],
             verdict[0], verdict[1], table)


def parser():
    usage = __doc__[__doc__.index("Usage:"):]
    raw = argparse.RawDescriptionHelpFormatter
    ap = argparse.ArgumentParser(prog="set_b.py", description=__doc__.splitlines()[0], epilog=usage,
                                 formatter_class=raw)
    sub = ap.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verdict", formatter_class=raw, epilog=usage,
                       help="apply the frozen rule of an id to a study's estimate and interval",
                       description="Apply the frozen came-true and did-not rules to a registered study's estimates "
                                   "and print the frozen words beside each verdict.")
    v.add_argument("csv", nargs="?", help="CSV with the columns id,estimate,lower,upper and, for F7, level "
                                          "(day or week_up; F7 needs both rows)")
    v.add_argument("--id", help="one prediction: " + ", ".join(RULES))
    v.add_argument("--estimate", type=float, help="the estimate (points for a difference of shares)")
    v.add_argument("--lower", type=float, help="the lower bound of the interval the rule reads")
    v.add_argument("--upper", type=float, help="the upper bound of the interval the rule reads")
    v.add_argument("--day", type=float, nargs=3, metavar=("ESTIMATE", "LOWER", "UPPER"),
                   help="F7 at Day: the odds ratio and its 90%% interval")
    v.add_argument("--week-up", type=float, nargs=3, metavar=("ESTIMATE", "LOWER", "UPPER"),
                   help="F7 at Week and above: the odds ratio and its 90%% interval")
    v.add_argument("--predictions", default=TABLE, help="the frozen table (default: predictions/predictions.csv)")
    v.set_defaults(run=cmd_verdict)

    d = sub.add_parser("diff", formatter_class=raw, epilog=usage,
                       help="difference of two shares with the Newcombe hybrid score interval",
                       description="Difference of two shares (group 1 minus group 2) in points, with the hybrid "
                                   "score interval of Newcombe (1998, method 10); --id applies a frozen rule.")
    d.add_argument("x1", type=int, help="count with the outcome in group 1 (F2, F3, F3b: people without IT "
                                        "education who passed; F4a: products abandoned; F12: vouched products "
                                        "reaching ten users)")
    d.add_argument("n1", type=int, help="people or products in group 1")
    d.add_argument("x2", type=int, help="count with the outcome in group 2 (programmers; unvouched products)")
    d.add_argument("n2", type=int, help="people or products in group 2")
    d.add_argument("--conf", type=float, help="confidence level (default 0.95, or the level the --id rule reads)")
    d.add_argument("--id", help="apply the rule of one of " + ", ".join(k for k, r in RULES.items()
                                                                          if r["scale"] == POINTS))
    d.add_argument("--predictions", default=TABLE, help="the frozen table (default: predictions/predictions.csv)")
    d.set_defaults(run=cmd_diff)

    o = sub.add_parser("or", formatter_class=raw, epilog=usage,
                       help="Mantel-Haenszel odds ratio over strata with the Robins-Breslow-Greenland interval",
                       description="Mantel-Haenszel odds ratio of passing, exposed group against the other, over "
                                   "strata, with the Robins-Breslow-Greenland interval; --id F7 applies its rule.")
    o.add_argument("csv", help="CSV with the columns stratum,group,passed,n and, for F7, level (day or week_up)")
    o.add_argument("--exposed", default="1", help="the group value of the exposed people (for F7, IT education; "
                                                  "default 1)")
    o.add_argument("--conf", type=float, help="confidence level (default 0.90, the level F7 reads)")
    o.add_argument("--id", help="F7: apply its rule to the odds ratios at Day and at Week and above")
    o.add_argument("--predictions", default=TABLE, help="the frozen table (default: predictions/predictions.csv)")
    o.set_defaults(run=cmd_or)

    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        args.run(args)
    except (ValueError, OSError, csv.Error, ArithmeticError) as e:
        sys.exit(f"set_b.py {args.command}: {e}")


if __name__ == "__main__":
    main()
