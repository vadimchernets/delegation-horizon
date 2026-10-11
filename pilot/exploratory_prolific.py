#!/usr/bin/env python3
"""exploratory_prolific.py: exploratory analyses of the Prolific pre-pilot (not registered).

The registered analysis is human_raters.py (OSF 10.17605/OSF.IO/V92R8). This script reuses its
loader and rules (exclusions, dropped estimates, the test "within a ratio of 1.5", rungs) and
changes none of them. Everything it prints is exploratory, not registered:
  0. control and accounting (participants paid, saved, kept; a 95% interval for the primary share);
  1. panel size: how many raters' median is needed for two independent panels to agree within 1.5;
  2. years in the field against a rater's level and against agreement;
  3. per-task spread: which tasks are most disputed;
  4. completion time and the unit chosen (hours or minutes) against agreement;
  5. raters excluded on the competency question against kept raters, in both domains;
  6. the retest: direction of the second answer.
Usage: python3 pilot/exploratory_prolific.py results/prolific-2026-10/ratings-long.csv \
           results/prolific-2026-10/participants.csv [task-bank-v0.csv]
Python 3.10 or later, standard library only; seed 20261011.
Licence: MIT
"""
import csv
import itertools
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from human_raters import calibrated, load, pair_share, rung  # noqa: E402  (registered rules)

SEED = 20261011
DOMAINS = ("bookkeeping", "webtools")
BANDS = ("Hour", "Day", "Week")
YEARS = ("Less than 1", "1-2", "3-5", "6-10", "More than 10")
PANELS = (1, 2, 3, 5, 7, 9, 11, 15, 21)
DRAWS = 2000


def within(a, b):
    return max(a, b) / min(a, b) <= 1.5  # the registered test, unchanged


def read_all(path):
    """Every estimate the registered rules keep, for kept and excluded raters alike."""
    data = defaultdict(lambda: defaultdict(dict))  # (domain, group) -> task -> rater -> hours
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ok = r["attention_ok"].strip() == "1" and r["competency_ok"].strip() == "1"
            try:
                h = float(r["reference_hours"])
            except ValueError:
                continue
            if 0 < h <= 2000:
                data[(r["domain"], "kept" if ok else "excluded")][r["task_id"]][r["rater"]] = h
    return data


def split(tasks):
    main = {t: r for t, r in tasks.items() if not t.endswith("-retest")}
    again = {t.replace("-retest", ""): r for t, r in tasks.items() if t.endswith("-retest")}
    return main, again


def complete(main):
    names = {w for r in main.values() for w in r}
    return sorted(w for w in names if all(w in main[t] for t in main))


def share(main, raters):
    hit = tot = 0
    for t in main:
        for a, b in itertools.combinations([w for w in raters if w in main[t]], 2):
            tot += 1
            hit += within(main[t][a], main[t][b])
    return hit / tot if tot else float("nan")


def others_median(main, t, who, pool):
    return statistics.median(main[t][u] for u in pool if u != who)


def level(main, w, pool):
    """A rater's level: mean log ratio of their estimate to the other raters' median."""
    return statistics.mean(math.log(main[t][w] / others_median(main, t, w, pool)) for t in main)


def distance(main, w, pool):
    """How far a rater sits from the others: mean absolute log ratio to the others' median."""
    return statistics.mean(abs(math.log(main[t][w] / others_median(main, t, w, pool))) for t in main)


def hit_rate(main, w, pool):
    return sum(within(main[t][w], others_median(main, t, w, pool)) for t in main) / len(main)


def ranks(v):
    order = sorted(range(len(v)), key=v.__getitem__)
    rk, i = [0.0] * len(v), 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2
        i = j + 1
    return rk


def spearman(x, y):
    return statistics.correlation(ranks(x), ranks(y))


def perm_p(xs, ys, reps, seed):
    """Two-sided permutation test on the difference of means."""
    g = random.Random(seed)
    pool, n = list(xs) + list(ys), len(xs)
    obs = abs(statistics.mean(ys) - statistics.mean(xs))
    hits = 0
    for _ in range(reps):
        g.shuffle(pool)
        hits += abs(statistics.mean(pool[n:]) - statistics.mean(pool[:n])) >= obs - 1e-12
    return hits / reps


def perm_rho(x, y, reps, seed):
    g = random.Random(seed)
    obs = abs(spearman(x, y))
    yy, hits = list(y), 0
    for _ in range(reps):
        g.shuffle(yy)
        hits += abs(spearman(x, yy)) >= obs - 1e-12
    return hits / reps


def sign_test(up, down):
    n, k = up + down, min(up, down)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot_interval(main, raters, reps, seed):
    """Resample raters with replacement; a pair of a rater with its own copy is skipped."""
    g = random.Random(seed)
    out = []
    for _ in range(reps):
        count = Counter(g.choice(raters) for _ in raters)
        hit = tot = 0.0
        for t in main:
            here = [(w, c) for w, c in count.items() if w in main[t]]
            for (a, ca), (b, cb) in itertools.combinations(here, 2):
                tot += ca * cb
                hit += ca * cb * within(main[t][a], main[t][b])
        out.append(hit / tot)
    out.sort()
    return out[int(0.025 * reps)], out[int(0.975 * reps) - 1]


def panels(main, pool, k, reps, g):
    """Two disjoint panels of k raters per task; share of draws whose medians agree within 1.5,
    and share on the same rung; also each panel's median against the full sample's median."""
    close = same = near_all = n = 0
    for t in sorted(main):
        full = statistics.median(main[t][w] for w in pool)
        for _ in range(reps):
            s = g.sample(pool, 2 * k)
            a = statistics.median(main[t][w] for w in s[:k])
            b = statistics.median(main[t][w] for w in s[k:])
            n += 1
            close += within(a, b)
            same += rung(a) == rung(b)
            near_all += within(a, full)
    return close / n, same / n, near_all / n


def third_rater_rate(main, pool, reps, g):
    """Rule of Section 5.2: two raters, a third when they differ by more than 1.5."""
    calls = n = 0
    for t in sorted(main):
        for _ in range(reps):
            a, b = g.sample(pool, 2)
            n += 1
            calls += not within(main[t][a], main[t][b])
    return calls / n


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    ratings_path, parts_path = sys.argv[1], sys.argv[2]
    bank_path = sys.argv[3] if len(sys.argv) > 3 else str(HERE / "task-bank-v0.csv")
    data = read_all(ratings_path)
    with open(parts_path, encoding="utf-8") as fh:
        parts = {(p["domain"], p["rater"]): p for p in csv.DictReader(fh)}
    with open(bank_path, encoding="utf-8") as fh:
        bank = {r["task_id"]: r["target_rung"] for r in csv.DictReader(fh)}
    g = random.Random(SEED)

    print("EXPLORATORY, NOT REGISTERED. The registered result is human-raters-output.txt.")
    reg_rows, _ = load(ratings_path)
    mine = {(d, w, t, h) for (d, grp), tasks in data.items() if grp == "kept"
            for t, r in tasks.items() for w, h in r.items()}
    print(f"control: kept estimates identical to the registered loader: "
          f"{'yes' if mine == set(reg_rows) else 'NO'} ({len(mine)} estimates)")

    mk, ak, mx, pool = {}, {}, {}, {}
    for d in DOMAINS:
        mk[d], ak[d] = split(data[(d, "kept")])
        mx[d], _ = split(data[(d, "excluded")])
        pool[d] = complete(mk[d])

    print("\n== 0. Accounting")
    print("paid: 119 (60 bookkeeping, 59 web tools); one web developer's answers were not saved by the"
          " survey tool, so 118 participants have answers")
    for i, d in enumerate(DOMAINS):
        n_all = sum(1 for (dd, _) in parts if dd == d)
        kept = sorted({w for r in mk[d].values() for w in r})
        excl = {w for r in mx[d].values() for w in r}
        lo, hi = boot_interval(mk[d], kept, DRAWS, SEED + i)
        print(f"{d}: {n_all} with answers, {len(kept)} kept, {len(excl)} excluded, {len(pool[d])} kept and complete;"
              f" pairs within 1.5 {pair_share(mk[d])[0]:.3f} (95% interval over raters {lo:.3f} to {hi:.3f})")
        print(f"   kept raters with a numeric estimate on fewer than all ten tasks: {len(kept) - len(pool[d])}")

    print(f"\n== 1. Panel size: two disjoint panels per task, {DRAWS} draws per task, kept complete raters")
    print("   columns: panel size; two panels' medians within 1.5; on the same rung; one panel's median within 1.5"
          " of the whole sample's median")
    for d in DOMAINS:
        print(f"{d} (raw estimates):")
        first = None
        for k in PANELS:
            if 2 * k > len(pool[d]):
                continue
            c, s, f = panels(mk[d], pool[d], k, DRAWS, g)
            if first is None and c >= 0.70:
                first = k
            print(f"   k={k}: {c:.3f}  {s:.3f}  {f:.3f}")
        print(f"   smallest panel tried with two panels within 1.5 in at least 70% of draws: {first or 'none up to 21'}")
        cal = calibrated({t: {w: mk[d][t][w] for w in pool[d]} for t in mk[d]})
        print(f"{d} (each rater's level removed, in sample, as in the registered secondary outcome):")
        for k in PANELS:
            c, s, f = panels(cal, pool[d], k, DRAWS, g)
            print(f"   k={k}: {c:.3f}  {s:.3f}  {f:.3f}")
        print(f"   rule of Section 5.2: a third rater is called on {third_rater_rate(mk[d], pool[d], DRAWS, g):.3f}"
              f" of pieces")

    print("\n== 2. Years in the field (kept complete raters)")
    for i, d in enumerate(DOMAINS):
        m, ws = mk[d], pool[d]
        lv = {w: level(m, w, ws) for w in ws}
        dist = {w: distance(m, w, ws) for w in ws}
        hr = {w: hit_rate(m, w, ws) for w in ws}
        yr = {w: YEARS.index(parts[(d, w)]["years_in_field"]) for w in ws}
        print(f"{d}:")
        for j, y in enumerate(YEARS):
            grp = [w for w in ws if yr[w] == j]
            if not grp:
                continue
            print(f"   {y:>12}: n {len(grp):2d}; level x{math.exp(statistics.mean(lv[w] for w in grp)):.2f};"
                  f" within 1.5 of the others' median {statistics.mean(hr[w] for w in grp):.2f};"
                  f" pairs within 1.5 inside the group {share(m, grp):.3f}")
        x = [yr[w] for w in ws]
        rl = spearman(x, [lv[w] for w in ws])
        rd = spearman(x, [dist[w] for w in ws])
        print(f"   rank correlation of years with level {rl:+.2f} (permutation p {perm_rho(x, [lv[w] for w in ws], 5000, SEED + 40 + i):.2f});"
              f" with distance from the others {rd:+.2f} (p {perm_rho(x, [dist[w] for w in ws], 5000, SEED + 50 + i):.2f})")
        sen = [w for w in ws if yr[w] == 4]
        rest = [w for w in ws if yr[w] < 4]
        print(f"   more than 10 years ({len(sen)}) against the rest ({len(rest)}): pairs within 1.5 {share(m, sen):.3f}"
              f" vs {share(m, rest):.3f}; level x{math.exp(statistics.mean(lv[w] for w in sen)):.2f}"
              f" vs x{math.exp(statistics.mean(lv[w] for w in rest)):.2f}"
              f" (p {perm_p([lv[w] for w in rest], [lv[w] for w in sen], 5000, SEED + 60 + i):.2f})")
    both = [(d, w) for d in DOMAINS for w in pool[d]]
    sen = [(d, w) for d, w in both if parts[(d, w)]["years_in_field"] == "More than 10"]
    print(f"both domains: {len(sen)} of {len(both)} kept complete raters report more than 10 years")

    print("\n== 3. Per-task spread (kept raters), most disputed first")
    rows = []
    for d in DOMAINS:
        for t in sorted(mk[d]):
            v = sorted(mk[d][t].values())
            q = statistics.quantiles(v, n=4)
            rows.append((pair_share({t: mk[d][t]})[0], t, bank.get(t, "?"),
                         statistics.median(v), q[0], q[2], v[0], v[-1]))
    for sh, t, b, med, q1, q3, lo, hi in sorted(rows):
        print(f"   {t} ({b}): pairs within 1.5 {sh:.3f}; median {med:g} h; quartiles {q1:g} to {q3:g}"
              f" (ratio {q3 / q1:.1f}); range {lo:g} to {hi:g}")
    for d in DOMAINS:
        for b in BANDS:
            r = [x for x in rows if x[1][:2] == ("BK" if d == "bookkeeping" else "WT") and x[2] == b]
            print(f"   {d}, tasks meant for {b}: mean pairs within 1.5 {statistics.mean(x[0] for x in r):.3f}")

    print("\n== 4. Completion time and unit chosen (kept complete raters)")
    for i, d in enumerate(DOMAINS):
        m, ws = mk[d], pool[d]
        tt = {w: int(parts[(d, w)]["time_taken_s"]) for w in ws if parts[(d, w)]["time_taken_s"].strip()}
        q = statistics.quantiles(sorted(tt.values()), n=4)
        fast = [w for w in ws if w in tt and tt[w] <= q[0]]
        slow = [w for w in ws if w in tt and tt[w] > q[0]]
        dist = {w: distance(m, w, ws) for w in ws}
        print(f"{d}: completion time median {statistics.median(tt.values()) / 60:.1f} min, fastest quarter at or under"
              f" {q[0] / 60:.1f} min ({len(fast)} raters)")
        print(f"   fastest quarter vs the rest: pairs within 1.5 {share(m, fast):.3f} vs {share(m, slow):.3f};"
              f" distance from the others x{math.exp(statistics.mean(dist[w] for w in fast)):.2f}"
              f" vs x{math.exp(statistics.mean(dist[w] for w in slow)):.2f}"
              f" (p {perm_p([dist[w] for w in slow], [dist[w] for w in fast], 5000, SEED + 70 + i):.2f});"
              f" rank correlation of time with distance {spearman([tt[w] for w in ws if w in tt], [dist[w] for w in ws if w in tt]):+.2f}")
        mins = [w for w in ws if int(parts[(d, w)]["n_minutes_answers"] or 0) > 0]
        hrs = [w for w in ws if w not in mins]
        print(f"   used minutes for at least one answer: {len(mins)}; hours only: {len(hrs)};"
              f" pairs within 1.5 {share(m, mins):.3f} vs {share(m, hrs):.3f};"
              f" distance x{math.exp(statistics.mean(dist[w] for w in mins)):.2f}"
              f" vs x{math.exp(statistics.mean(dist[w] for w in hrs)):.2f}"
              f" (p {perm_p([dist[w] for w in hrs], [dist[w] for w in mins], 5000, SEED + 80 + i):.2f})")
        hour_tasks = [t for t in m if bank.get(t) == "Hour"]
        big = [w for w in ws if max(m[t][w] for t in hour_tasks) >= 40]
        print(f"   raters with an estimate of 40 h or more on a task meant for Hour (possible minutes typed as hours):"
              f" {len(big)}; pairs within 1.5 without them {share(m, [w for w in ws if w not in big]):.3f}")

    print("\n== 5. Excluded (failed the competency question) against kept raters")
    for i, d in enumerate(DOMAINS):
        k_, x_ = mk[d], mx[d]
        kept, excl = pool[d], complete(x_)
        week = [t for t in sorted(k_) if bank.get(t) == "Week"]
        hour = [t for t in sorted(k_) if bank.get(t) == "Hour"]
        print(f"{d}: {len(excl)} excluded with all ten estimates; medians of tasks meant for Week, excluded "
              + ", ".join(f"{statistics.median(x_[t].values()):g}" for t in week) + "; kept "
              + ", ".join(f"{statistics.median(k_[t].values()):g}" for t in week))
        print("   medians of tasks meant for Hour, excluded "
              + ", ".join(f"{statistics.median(x_[t].values()):g}" for t in hour) + "; kept "
              + ", ".join(f"{statistics.median(k_[t].values()):g}" for t in hour))

        def wh(m, w):
            return (statistics.mean(math.log(m[t][w]) for t in week)
                    - statistics.mean(math.log(m[t][w]) for t in hour))
        xs = [wh(k_, w) for w in kept]
        ys = [wh(x_, w) for w in excl]
        print(f"   own Week tasks over own Hour tasks (a rater's level cancels): geometric mean, excluded"
              f" x{math.exp(statistics.mean(ys)):.1f}, kept x{math.exp(statistics.mean(xs)):.1f};"
              f" permutation p {perm_p(xs, ys, 10000, SEED + 90 + i):.2f}")
        allw = [statistics.mean(math.log(k_[t][w]) for t in k_) for w in kept]
        allx = [statistics.mean(math.log(x_[t][w]) for t in x_) for w in excl]
        print(f"   overall level, excluded/kept x{math.exp(statistics.mean(allx) - statistics.mean(allw)):.2f}"
              f" (p {perm_p(allw, allx, 10000, SEED + 95 + i):.2f}); pairs within 1.5 among the excluded"
              f" {pair_share(x_)[0]:.3f}")

    print("\n== 6. Retest: the repeated task asked again after all ten (kept raters)")
    for d in DOMAINS:
        m, a = mk[d], ak[d]
        prs = [(m[t][w], h) for t, r in a.items() for w, h in r.items() if w in m[t]]
        up = sum(b > x for x, b in prs)
        down = sum(b < x for x, b in prs)
        print(f"{d}: n {len(prs)}; second answer higher {up}, lower {down}, equal {len(prs) - up - down};"
              f" exact sign test p {sign_test(up, down):.4f}; geometric mean second/first"
              f" {math.exp(statistics.mean(math.log(b / x) for x, b in prs)):.2f}")


if __name__ == "__main__":
    main()
