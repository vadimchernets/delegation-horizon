#!/usr/bin/env python3
"""figure_a1_calendar.py: Figure A1 of the paper, the calendar of checks, drawn from the prediction table itself.

Teaches: every registered prediction is a dated test. One row per prediction of predictions/predictions.csv, sorted by
the start of its check: a filled dot for a check on a fixed day, a light bar for a check in a year or a data year, a
ring at the final date (no comparable data by then means unresolved), the annual scorecards from October 2027 to
2031, and two commitments that fall due before any check: the F27 sample, frozen on Zenodo by 31 December 2026 (its
measure), and the protocol of every Set B study, registered by 30 June 2027 (the registration_deadline column), or
the prediction is recorded as not conducted. Every date, label and probability comes from the table; one title (F32)
is shortened to fit its column, in the words of predictions/changelog-v1-v2.md, and the RevenueCat report is drawn in
spring, when it is published, labelled as the table names it ("2027 report").
Needs matplotlib (the figure is drawn, nothing is computed).
Usage: python3 figures/figure_a1_calendar.py [--out figure-A1-calendar]  (writes .png and .svg, the same bytes on
every run)
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "predictions", "predictions.csv")

INK, GREY, LINE, ACCENT, FILL, SHADE, YEARS = "#1a1a1a", "#4a4a4a", "#8a8a8a", "#1a4d8f", "#dce5f2", "#f5f5f5", "#bdbdbd"
W_MM, H_MM = 240.0, 170.0
REGISTERED = dt.date(2026, 10, 9)
SCORECARDS = [dt.date(y, 10, 9) for y in range(2027, 2032)]
X0, PER_YEAR = 94.2, 27.53            # mm: where 1 January 2027 falls, and the width of one year
TOP_ROW, PITCH = 153.1, 3.27          # mm: centre of the first row, and the distance between rows
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
SEASONS = {"RevenueCat": (3, 6)}   # a report published in a known season of its year (March to June)
# the one title too long for its column, shortened in the words of predictions/changelog-v1-v2.md (the vendor stays)
SHORT = {"F32": "Vendor reports non-developer majority"}
ID_X, TITLE_X, P_X = 3.0, 11.5, 75.4           # mm: the three text columns


def x_of(day):
    start = dt.date(day.year, 1, 1)
    length = (dt.date(day.year + 1, 1, 1) - start).days
    return X0 + (day.year - 2027 + (day - start).days / length) * PER_YEAR


def parse_day(text):
    m = re.fullmatch(r"\s*(\d{1,2}) ([A-Za-z]+) (\d{4})\s*", text or "")
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))


def check_span(text, final):
    """(kind, start, end, label) for a check date as the table writes it."""
    day = parse_day(text)
    if day:
        return "day", day, day, ""
    m = re.fullmatch(r"(\w+) (\d{4}) report", text)
    if m and m.group(1) in SEASONS:
        first, last = SEASONS[m.group(1)]
        year = int(m.group(2))
        return "bar", dt.date(year, first, 1), dt.date(year, last + 1, 1) - dt.timedelta(days=1), f"{year} report"
    m = re.fullmatch(r"(?:(\w+) report )?(\d{4})( data)?", text)
    if m:
        year = int(m.group(2))
        return "bar", dt.date(year, 1, 1), dt.date(year, 12, 31), text
    if text.lower().startswith("publication of"):
        return "on", dt.date(final.year - 1, 12, 31), final, "on " + text[0].lower() + text[1:]
    raise ValueError(f"check date not understood: {text!r}")


def rows(path=TABLE):
    with open(path, newline="", encoding="utf-8") as fh:
        table = list(csv.DictReader(fh))
    out = []
    for order, r in enumerate(table):
        final = parse_day(r["final_date"])
        kind, start, end, label = check_span(r["check_date"], final)
        out.append({"id": r["id"], "title": SHORT.get(r["id"], r["prediction"].split(" (")[0]), "p": r["probability"],
                    "set": r["set"],
                    "kind": kind, "start": start, "end": end, "label": label, "final": final, "order": order,
                    "freeze": parse_day((re.search(r"frozen on \w+ by (\d{1,2} \w+ \d{4})", r["measure"]) or
                                         [None, ""])[1]),
                    "deadline": parse_day((re.search(r"by (\d{1,2} \w+ \d{4})", r["registration_deadline"] or "") or
                                           [None, ""])[1])})
    return sorted(out, key=lambda r: (r["start"], r["final"], r["order"]))


def draw(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    plt.rcParams.update({"font.family": ["Arial", "Helvetica", "DejaVu Sans"], "svg.fonttype": "path",
                         "svg.hashsalt": "figure-A1"})
    items = rows()
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.axis("off")
    y = [TOP_ROW - i * PITCH for i in range(len(items))]
    bottom, top = y[-1] - PITCH / 2, y[0] + PITCH / 2
    left, right = x_of(REGISTERED), W_MM - 2.4

    for i, yy in enumerate(y):
        if i % 2 == 0:
            ax.add_patch(Rectangle((2.0, yy - PITCH / 2), right - 2.0, PITCH, fc=SHADE, ec="none", zorder=0))
    for year in range(2027, 2033):
        x = x_of(dt.date(year, 1, 1))
        ax.plot([x, x], [bottom, top], color=YEARS, lw=0.6, zorder=1)
        ax.text(x, bottom - 4.4, str(year), ha="center", va="center", fontsize=8.5, color=INK)
    for day in SCORECARDS:
        x = x_of(day)
        ax.plot([x, x], [bottom, top], color=ACCENT, lw=0.7, ls=(0, (0.7, 1.4)), zorder=1)
        ax.text(x, top + 3.3, "annual scorecard", ha="center", va="center", fontsize=7.5, color=ACCENT)
    ax.plot([left, left], [bottom, top], color=ACCENT, lw=1.4, zorder=2)
    ax.text(107.4, top + 7.8, "OSF registration, October 2026", ha="center", va="center", fontsize=8.0,
            color=ACCENT, weight="bold")
    ax.text(P_X, top + 3.3, "p", ha="center", va="center", fontsize=7.5, color=INK, style="italic")

    deadline = next((r["deadline"] for r in items if r["deadline"]), None)
    if deadline:
        x = x_of(deadline)
        ax.plot([x, x], [bottom, top], color=ACCENT, lw=0.8, ls=(0, (3.0, 1.6)), zorder=1)
    for r, yy in zip(items, y):
        ax.text(ID_X, yy, r["id"], ha="left", va="center", fontsize=7.8, color=INK, weight="bold")
        ax.text(TITLE_X, yy, r["title"], ha="left", va="center", fontsize=7.5, color=INK)
        ax.text(P_X, yy, r["p"], ha="center", va="center", fontsize=7.5, color=GREY)
        xf = x_of(r["final"])
        if r["kind"] == "on":
            ax.plot([left, xf], [yy, yy], color=GREY, lw=0.8, ls=(0, (1.8, 1.8)), zorder=2)
            ax.text(xf - 1.6, yy + 0.15, r["label"], ha="right", va="center", fontsize=7.0, color=GREY,
                    style="italic", zorder=3, bbox={"fc": SHADE if items.index(r) % 2 == 0 else "white",
                                                    "ec": "none", "pad": 0.3})
        else:
            xs, xe = x_of(r["start"]), x_of(r["end"])
            ax.plot([xe, xf], [yy, yy], color=LINE, lw=1.0, zorder=2)
            if r["kind"] == "bar":
                ax.add_patch(Rectangle((xs, yy - 1.05), xe - xs, 2.1, fc=FILL, ec=ACCENT, lw=0.6, zorder=3))
                if xe - xs >= 12.0:
                    ax.text((xs + xe) / 2, yy, r["label"], ha="center", va="center", fontsize=7.0, color=ACCENT,
                            zorder=4)
                else:                                   # a short bar (a spring report): the label stands before it
                    ax.text(xs - 0.8, yy, r["label"], ha="right", va="center", fontsize=7.0, color=ACCENT, zorder=4)
            else:
                ax.plot([xs], [yy], marker="o", ms=4.6, mfc=ACCENT, mec=ACCENT, zorder=5)
        ax.plot([xf], [yy], marker="o", ms=4.6, mfc="white", mec=INK, mew=1.0, zorder=5)
        if r["set"] == "B" and r["deadline"]:
            # drawn over the dot, hollow and a little larger: F34's deadline falls on its check day
            ax.plot([x_of(r["deadline"])], [yy], marker="s", ms=7.4, mfc="none", mec=ACCENT, mew=0.9, zorder=6)
        if r["freeze"]:
            xz = x_of(r["freeze"])
            ax.plot([xz, x_of(r["start"])], [yy, yy], color=LINE, lw=0.7, ls=(0, (0.7, 1.4)), zorder=2)
            ax.plot([xz], [yy], marker="s", ms=7.4, mfc="white", mec=ACCENT, mew=0.9, zorder=4)
            ax.text(xz + 1.6, yy + 0.15, "sample frozen", ha="left", va="center", fontsize=6.6, color=ACCENT,
                    style="italic", zorder=4, bbox={"fc": SHADE if items.index(r) % 2 == 0 else "white",
                                                     "ec": "none", "pad": 0.25})

    ly = bottom - 9.6
    legend = [(Line2D([], [], marker="o", ls="none", ms=4.6, mfc=ACCENT, mec=ACCENT), "check on a fixed day"),
              (Rectangle((0, 0), 1, 1, fc=FILL, ec=ACCENT, lw=0.6), "check in a year or data year, no fixed day"),
              (Line2D([], [], marker="o", ls="none", ms=4.6, mfc="white", mec=INK), "final date: no comparable data by "
                                                                                    "then means unresolved")]
    for i, (handle, text) in enumerate(legend):
        yy = ly - i * 3.75
        if isinstance(handle, Rectangle):
            ax.add_patch(Rectangle((2.8, yy - 1.0), 3.6, 2.0, fc=FILL, ec=ACCENT, lw=0.6))
        else:
            ax.plot([4.6], [yy], marker="o", ms=4.6, mfc=handle.get_markerfacecolor(),
                    mec=handle.get_markeredgecolor(), mew=1.0)
        ax.text(7.6, yy, text, ha="left", va="center", fontsize=7.5, color=GREY)
    ax.plot([96.0], [ly], marker="s", ms=7.4, mfc="white", mec=ACCENT, mew=0.9)
    ax.text(98.6, ly, "due before the check: the F27 sample frozen on Zenodo, and every Set B protocol",
            ha="left", va="center", fontsize=7.5, color=GREY)
    ax.text(98.6, ly - 3.75, "registered by the dashed line of 30 June 2027, or recorded as not conducted",
            ha="left", va="center", fontsize=7.5, color=GREY)
    ax.text(right - 0.6, ly - 6.6, "Each date is a test", ha="right", va="center", fontsize=10.0, color=INK,
            weight="bold")
    fig.savefig(out + ".png", dpi=3000 / (W_MM / 25.4), facecolor="white", metadata={"Software": None})
    fig.savefig(out + ".svg", facecolor="white", metadata={"Date": None, "Creator": None})
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Draw Figure A1, the calendar of checks, from predictions.csv.")
    ap.add_argument("--out", default="figure-A1-calendar", help="file name without extension (.png and .svg)")
    args = ap.parse_args()
    draw(args.out)
    print(f"written {args.out}.png and {args.out}.svg from {len(rows())} predictions")


if __name__ == "__main__":
    main()
