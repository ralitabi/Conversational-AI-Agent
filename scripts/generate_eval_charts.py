"""
Generate evaluation charts for poster.
Run from project root:  python scripts/generate_eval_charts.py
Outputs three PNG files to docs/evaluation/
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "evaluation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Colour palette ────────────────────────────────────────────────────────────
PASS_COL    = "#2ecc71"   # green
PARTIAL_COL = "#f39c12"   # amber
FAIL_COL    = "#e74c3c"   # red
ACCENT      = "#2c3e7a"   # deep navy (Bradford-ish)
LIGHT_BG    = "#f7f9fc"
FONT        = "DejaVu Sans"

plt.rcParams.update({
    "font.family":       FONT,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.facecolor":    LIGHT_BG,
    "figure.facecolor":  "white",
})

# ── Data ─────────────────────────────────────────────────────────────────────
services     = ["Council Tax", "Library\nServices", "Bin\nCollection", "Benefits\nSupport"]
pass_counts  = [2, 7, 3, 4]
part_counts  = [0, 1, 1, 0]
fail_counts  = [0, 1, 0, 2]
totals       = [p + w + f for p, w, f in zip(pass_counts, part_counts, fail_counts)]
pass_rates   = [p / t * 100 for p, t in zip(pass_counts, totals)]

metrics      = ["Intent\nClassification", "Service\nRouting", "RAG Answer\nAccuracy", "Multi-turn Flow\nCompletion", "Overall\nPass Rate"]
metric_vals  = [86, 91, 89, 71, 77]

scenarios = [
    ("Library",       "How do I join?",                   "pass"),
    ("Library",       "Can I search books online?",        "pass"),
    ("Library",       "Library opening hours",             "partial"),
    ("Library",       "Find library near BD1 1HY",         "pass"),
    ("Library",       "Find library in Bingley",           "pass"),
    ("Library",       "Select library result → '1'",       "fail"),
    ("Library",       "Home Library Service info",         "pass"),
    ("Library",       "eBooks available?",                 "pass"),
    ("Library",       "Library finder + skip postcode",    "pass"),
    ("Bin",           "What bin for cardboard?",           "pass"),
    ("Bin",           "When is my bin collected?",         "pass"),
    ("Bin",           "Postcode entered directly",         "partial"),
    ("Bin",           "Service disruption query",          "pass"),
    ("Council Tax",   "How does council tax work?",        "pass"),
    ("Council Tax",   "What is my CT band? + postcode",    "pass"),
    ("Benefits",      "Housing benefit eligibility (5-turn)", "pass"),
    ("Benefits",      "Benefits flow: pensioner + rent",   "pass"),
    ("Benefits",      "'benefits calculator' in service",  "pass"),
    ("Benefits",      "Full calculator flow to result",    "pass"),
    ("Benefits",      "'benefits calculator' at root",     "fail"),
    ("Benefits",      "'benefits' at root menu",           "fail"),
    ("Benefits",      "Out-of-order inputs at root",       "pass"),
]

# ── Chart 1: Stacked bar — results per service ────────────────────────────────
fig1, ax1 = plt.subplots(figsize=(7, 3.6))

x = np.arange(len(services))
bar_w = 0.52

p1 = ax1.bar(x, pass_counts,  bar_w, label="Pass",    color=PASS_COL,    zorder=3)
p2 = ax1.bar(x, part_counts,  bar_w, bottom=pass_counts, label="Partial", color=PARTIAL_COL, zorder=3)
p3 = ax1.bar(x, fail_counts,  bar_w,
             bottom=[p + w for p, w in zip(pass_counts, part_counts)],
             label="Fail", color=FAIL_COL, zorder=3)

# pass-rate labels above each bar
for i, (rate, total) in enumerate(zip(pass_rates, totals)):
    ax1.text(i, total + 0.12, f"{rate:.0f}%", ha="center", va="bottom",
             fontsize=10, fontweight="bold", color=ACCENT)

ax1.set_xticks(x)
ax1.set_xticklabels(services, fontsize=10)
ax1.set_ylabel("Test Scenarios", fontsize=10)
ax1.set_ylim(0, max(totals) + 1.4)
ax1.set_yticks(range(0, max(totals) + 2))
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: int(v)))
ax1.set_title("Test Results by Service Area", fontsize=13, fontweight="bold",
              color=ACCENT, pad=10)
ax1.legend(loc="upper right", framealpha=0.9, fontsize=9)
ax1.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
ax1.set_facecolor(LIGHT_BG)

fig1.tight_layout()
fig1.savefig(OUT_DIR / "eval_by_service.png", dpi=180, bbox_inches="tight")
plt.close(fig1)
print(f"Saved: {OUT_DIR / 'eval_by_service.png'}")

# ── Chart 2: Horizontal bar — key metrics ────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(6.5, 3.6))

y = np.arange(len(metrics))
bar_h = 0.48

colours = [PASS_COL if v >= 80 else PARTIAL_COL for v in metric_vals]
bars = ax2.barh(y, metric_vals, bar_h, color=colours, zorder=3)

# value labels
for bar, val in zip(bars, metric_vals):
    ax2.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
             f"{val}%", va="center", fontsize=10, fontweight="bold", color=ACCENT)

ax2.set_yticks(y)
ax2.set_yticklabels(metrics, fontsize=10)
ax2.set_xlim(0, 108)
ax2.set_xlabel("Score (%)", fontsize=10)
ax2.set_title("Performance Metrics", fontsize=13, fontweight="bold",
              color=ACCENT, pad=10)
ax2.axvline(80, color="#bdc3c7", linestyle="--", linewidth=1, zorder=2)
ax2.text(80.5, -0.65, "80% target", fontsize=8, color="#7f8c8d")
ax2.grid(axis="x", linestyle="--", alpha=0.5, zorder=0)
ax2.set_facecolor(LIGHT_BG)

fig2.tight_layout()
fig2.savefig(OUT_DIR / "eval_metrics.png", dpi=180, bbox_inches="tight")
plt.close(fig2)
print(f"Saved: {OUT_DIR / 'eval_metrics.png'}")

# ── Chart 3: Scenario grid (heat-map style) ──────────────────────────────────
colour_map = {"pass": PASS_COL, "partial": PARTIAL_COL, "fail": FAIL_COL}
label_map  = {"pass": "✓", "partial": "~", "fail": "✗"}

n = len(scenarios)
cols = 4
rows = int(np.ceil(n / cols))

fig3, ax3 = plt.subplots(figsize=(10, rows * 0.85 + 1.2))
ax3.set_xlim(0, cols)
ax3.set_ylim(0, rows)
ax3.axis("off")
ax3.set_title("Scenario-Level Results  (22 test cases)", fontsize=13,
              fontweight="bold", color=ACCENT, pad=12)

for idx, (service, desc, outcome) in enumerate(scenarios):
    col = idx % cols
    row = rows - 1 - (idx // cols)      # top-to-bottom reading order

    col_fill = colour_map[outcome]
    rect = mpatches.FancyBboxPatch(
        (col + 0.06, row + 0.08), 0.88, 0.78,
        boxstyle="round,pad=0.03",
        facecolor=col_fill, alpha=0.18,
        edgecolor=col_fill, linewidth=1.5,
    )
    ax3.add_patch(rect)

    # outcome badge (top-right corner)
    ax3.text(col + 0.88, row + 0.74, label_map[outcome],
             fontsize=11, fontweight="bold", color=col_fill,
             ha="right", va="top")

    # service label
    ax3.text(col + 0.12, row + 0.72, service,
             fontsize=7.5, fontweight="bold", color=ACCENT,
             ha="left", va="top")

    # query description — wrap manually
    words = desc.split()
    lines, line = [], ""
    for w in words:
        test_line = (line + " " + w).strip()
        if len(test_line) <= 24:
            line = test_line
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    wrapped = "\n".join(lines[:2])   # max 2 display lines

    ax3.text(col + 0.12, row + 0.50, wrapped,
             fontsize=7.8, color="#2d3436",
             ha="left", va="top", linespacing=1.3)

# Legend
legend_y = -0.05
for i, (outcome, label, colour) in enumerate([
    ("pass",    "Pass (17)",    PASS_COL),
    ("partial", "Partial (2)",  PARTIAL_COL),
    ("fail",    "Fail (3)",     FAIL_COL),
]):
    rx = 0.2 + i * 1.3
    rect = mpatches.FancyBboxPatch(
        (rx, legend_y), 0.28, 0.28,
        boxstyle="round,pad=0.03",
        facecolor=colour, alpha=0.25,
        edgecolor=colour, linewidth=1.5,
    )
    ax3.add_patch(rect)
    ax3.text(rx + 0.36, legend_y + 0.14, label,
             fontsize=9, va="center", color=ACCENT)

fig3.tight_layout()
fig3.savefig(OUT_DIR / "eval_scenarios.png", dpi=180, bbox_inches="tight")
plt.close(fig3)
print(f"Saved: {OUT_DIR / 'eval_scenarios.png'}")

print(f"\nAll charts saved to {OUT_DIR}")
print("  eval_by_service.png  — stacked bar by service")
print("  eval_metrics.png     — horizontal bar for key metrics")
print("  eval_scenarios.png   — scenario grid overview")
