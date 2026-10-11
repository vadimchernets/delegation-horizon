#!/usr/bin/env python3
"""figure_a4_checking_process.py: Figure A4 of the paper, the checking process of Section 6.5.

Teaches: what each of the four steps of Section 6.5 stands in for, what it earns under rules v1.1 (the same sets
of checks that horizon.py counts), where it stops, and how planted errors of both kinds measure the rest. The
credit row is read from horizon.py, so a change of the rules shows in the figure.
Needs matplotlib (the only file of the repository that does; the figure is drawn, nothing is computed).
Usage: python3 figures/figure_a4_checking_process.py [--out figure-A4-checking-process]  (writes .png and .svg)
Licence: MIT
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402  (the rules of Appendix C2)

INK, GREY, LINE, ACCENT, FILL, RULE = "#1a1a1a", "#4a4a4a", "#8a8a8a", "#1a4d8f", "#dce5f2", "#d0d0d0"
W_MM, H_MM = 160, 96
STEPS = [("1  list before\nthe work", "what it must contain,\nwhat is forgotten,\nwhich checks apply"),
         ("2  one agent\nmakes it", "with the task,\nthe material\nand the list"),
         ("3  fresh review", "same family,\na new session\nwithout the history"),
         ("4  another\nfamily", "checks against\nsources the person\nopened"),
         ("check the agents\ndid not see", "hidden tests,\na qualified reviewer\nor real use")]
# the log value each column is recorded as, and whether the rule counts it (from horizon.py)
RECORDED = [None, None, "same_family", "other_family_with_sources", "hidden_tests"]
NO_CREDIT = {0} | {i for i, value in enumerate(RECORDED) if value and value not in horizon.INDEPENDENT}


def credit_row():
    """The 'earns' row, checked against the rule: same_family never verifies, the others do."""
    assert "same_family" not in horizon.INDEPENDENT
    assert {"other_family_with_sources", "hidden_tests", "expert", "real_use"} <= horizon.INDEPENDENT
    return ["no credit: part of\nthe statement of done", "the work that\nis checked", "same_family:\nno credit",
            "counts with sources;\nnever alone for\nirreversible work", "counts"]


ROWS = [("stands in for", 53.0, ["knowing what the\nwork must contain", "the making", "a second look\nat what was made",
                                 "a second look,\nwith other errors", ""]),
        ("earns under\nrules v1.1", 39.0, credit_row()),
        ("where it\nstops", 24.0, ["an omission it does\nnot name reaches\nno reviewer", "",
                                   "its errors coincide\nwith the agents' own", "errors correlate\nacross families too", ""])]


def draw(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    plt.rcParams.update({"font.family": ["Arial", "Helvetica", "DejaVu Sans"], "svg.fonttype": "path",
                         "svg.hashsalt": "figure-A4"})
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.axis("off")

    def box(x, y, w, h, edge=LINE, face="white", lw=1.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.8", fc=face, ec=edge, lw=lw))

    def text(x, y, s, size=6.8, color=INK, weight="normal", ha="center", style="normal"):
        ax.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va="center", style=style, linespacing=1.22)

    x0, cw, gap = 20.0, 25.4, 2.9
    centre = [x0 + cw / 2 + i * (cw + gap) for i in range(5)]
    top, th = 63.0, 25.0
    for i, (title, sub) in enumerate(STEPS):
        last = i == 4
        box(centre[i] - cw / 2, top, cw, th, edge=ACCENT if last else LINE, face=FILL if last else "white",
            lw=1.5 if last else 1.0)
        text(centre[i], top + th - 6.2, title, size=7.6, weight="bold", color=ACCENT if last else INK)
        text(centre[i], top + 7.4, sub, size=6.3, color=GREY)
        if i < 4:
            ax.add_patch(FancyArrowPatch((centre[i] + cw / 2 + 0.2, top + th / 2),
                                         (centre[i + 1] - cw / 2 - 0.2, top + th / 2),
                                         arrowstyle="-|>", mutation_scale=6, color=GREY, lw=0.9, shrinkA=0, shrinkB=0))
    for label, y, cells in ROWS:
        text(1.2, y, label, size=6.6, color=GREY, ha="left", style="italic")
        for i, s in enumerate(cells):
            if not s:
                continue
            credit = label.startswith("earns")
            counts = credit and RECORDED[i] in horizon.INDEPENDENT
            none = credit and i in NO_CREDIT
            text(centre[i], y, s, size=6.4, color=ACCENT if counts else (LINE if none else INK),
                 weight="bold" if counts else "normal")
    for y in (46.5, 31.5):
        ax.plot([x0 - 1, W_MM - 1.5], [y, y], color=RULE, lw=0.6)
    box(x0 - 1, 6.8, W_MM - x0 - 0.5, 10.4, edge=ACCENT, lw=1.1)
    text((x0 - 1 + W_MM - 1.5) / 2, 12.0,
         "Planted errors of both kinds show where the process stops: wrong entries, which a reviewer\n"
         "can find, and omissions, which only the list names. Section 10.5 crosses experience with the way of working.",
         size=6.6, color=ACCENT)
    text(W_MM / 2, 2.6, "A process for checking: what each step stands in for, and what it earns", size=8.6, weight="bold")
    fig.savefig(out + ".png", dpi=2000 / (W_MM / 25.4), facecolor="white")
    fig.savefig(out + ".svg", facecolor="white", metadata={"Date": None})
    plt.close(fig)
    return out + ".png", out + ".svg"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draw Figure A4 (the checking process of Section 6.5).")
    ap.add_argument("--out", default="figure-A4-checking-process", help="path without extension")
    args = ap.parse_args(argv)
    for path in draw(args.out):
        print("wrote", path)


if __name__ == "__main__":
    main()
