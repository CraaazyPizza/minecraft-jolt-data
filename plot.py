"""Regenerate the per-run plots and overview from the published JSON files."""

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

plt.switch_backend("Agg")

ROOT = Path(__file__).resolve().parent
GREEN = "#24644f"
PAPER = "#f6f5ef"
INK = "#19372b"


def resolved_segments(data):
    """Return separate resolved segments as (video seconds, GUI seconds) pairs."""
    observations = data["observations"]
    segments = []
    for segment in data.get("segments", []):
        if segment.get("ambiguous", False):
            continue
        points = []
        for assignment in segment.get("assignments", []):
            if assignment.get("matching_tick_ambiguous", False):
                continue
            event = observations[assignment["event_index"]]
            x = float(event["seconds"])
            y = float(assignment["tick"]) / 20
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("Non-finite observation or GUI tick")
            points.append((x, y))
        if points:
            segments.append(sorted(points))
    if not segments:
        return []
    x0, y0 = min(point for segment in segments for point in segment)
    return [[(x - x0, y - y0) for x, y in segment] for segment in segments]


def draw(ax, segments, small=False):
    ax.set_xscale("linear")
    ax.set_yscale("linear")
    ax.set_aspect("equal", adjustable="box")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8 if small else 9, colors="#65756b", length=2.5, width=0.6)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#a8b3a9")
        ax.spines[spine].set_linewidth(0.6)
    ax.ticklabel_format(style="plain", useOffset=False)
    if not segments:
        ax.text(0.5, 0.5, "No resolved data", ha="center", va="center",
                transform=ax.transAxes, fontsize=6 if small else 12, color="#777777")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        points = [point for segment in segments for point in segment]
        lower = min(0, *(y for _, y in points))
        upper = max(1, *(x for x, _ in points), *(y for _, y in points))
        padding = (upper - lower) * 0.04
        ax.plot([lower, upper], [lower, upper], color="#b2bcb1", linewidth=0.8,
                linestyle="--", zorder=0, label="Equal elapsed time")
        for segment in segments:
            x, y = zip(*segment)
            ax.plot(x, y, color=GREEN, linewidth=1 if small else 0.7,
                    marker=".", markersize=2 if small else 2.5)
        ax.set_xlim(lower - padding, upper + padding)
        ax.set_ylim(lower - padding, upper + padding)
        ax.locator_params(axis="both", nbins=2 if small else 6)
    assert ax.get_xscale() == ax.get_yscale() == "linear"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "data/index.json")
    parser.add_argument("--output", type=Path, default=ROOT / "plots")
    parser.add_argument("--overview-only", action="store_true")
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    runs = sorted(index["runs"], key=lambda run: run["rank"])
    ranks = [run["rank"] for run in runs]
    if len(ranks) != len(set(ranks)):
        raise ValueError("Duplicate leaderboard ranks")
    args.output.mkdir(parents=True, exist_ok=True)
    overview, axes = plt.subplots(10, 10, figsize=(25, 28.75), facecolor=PAPER)
    overview.text(0.055, 0.963, "The hunger-bar clock in 100 Minecraft speedruns",
                  fontsize=37, fontweight="bold", color=INK)
    overview.text(0.055, 0.936, "Java 1.16.1 / Any% Glitchless / Random Seed",
                  fontsize=21, color="#65756b")
    overview.legend(
        [plt.Line2D([], [], color=GREEN, linewidth=2.5),
         plt.Line2D([], [], color="#a8b3a9", linewidth=1.5, linestyle="--")],
        ["Clock recovered from hunger-bar jolts", "Equal elapsed time"],
        loc="lower left", bbox_to_anchor=(0.049, 0.894), ncols=2, frameon=False,
        fontsize=17, labelcolor=INK, handlelength=2.7, columnspacing=2.5,
    )
    overview.text(0.018, 0.49, "Elapsed GUI clock time (seconds)", rotation=90,
                  va="center", ha="center", fontsize=20, color=INK)
    overview.text(0.52, 0.088, "Elapsed video time (seconds)",
                  ha="center", fontsize=20, color=INK)
    overview.text(0.055, 0.053,
                  "Green = usable timing data. Only resolved sections are drawn. Zero = first resolved jolt. Linear axes, equal scale per panel.",
                  fontsize=15, color=INK)
    overview.text(0.055, 0.033,
                  "Menus, other attempts and credits may appear. Some timing gaps remain unresolved. This does not certify runs.",
                  fontsize=15, color="#65756b")
    overview.text(0.055, 0.014, "Data and code: github.com/CraaazyPizza/minecraft-jolt-data",
                  fontsize=12, color="#65756b")
    overview.text(0.985, 0.014, "Leaderboard snapshot: 15 Oct 2026",
                  fontsize=12, color="#65756b", ha="right")
    by_rank = {run["rank"]: run for run in runs}
    for rank, ax in enumerate(axes.flat, start=1):
        run = by_rank.get(rank)
        proof = max(run.get("proofs", []), key=lambda p: p.get("supported_events", 0),
                    default=None) if run else None
        segments = []
        if proof and proof.get("data_file"):
            path = (args.index.parent.parent / proof["data_file"]).resolve()
            data = json.loads(path.read_text())
            segments = resolved_segments(data)
        draw(ax, segments, small=True)
        ax.set_facecolor(PAPER)
        ax.set_title(f"#{rank}", fontsize=12, pad=7, loc="left", color=GREEN, fontweight="bold")
        if not run or args.overview_only:
            continue
        fig, detail = plt.subplots(figsize=(6.4, 5.5))
        draw(detail, segments)
        detail.set_title(f"Rank {rank}: {run['run_id']}", fontsize=12)
        detail.set_xlabel("Video elapsed (s)")
        detail.set_ylabel("GUI clock elapsed (s)")
        fig.text(0.5, 0.045, "Time zero: first resolved jolt. Proof may include menus, credits or other attempts.",
                 ha="center", fontsize=7)
        fig.text(0.5, 0.018, "Dashed line: equal elapsed time. Separate segments are not joined.",
                 ha="center", fontsize=7, color="#555555")
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        fig.savefig(args.output / f"{rank:03d}-{run['run_id']}.png", dpi=120,
                    facecolor="white", metadata={"Software": "plot.py"})
        plt.close(fig)
    overview.subplots_adjust(left=0.055, right=0.985, top=0.872, bottom=0.12,
                             wspace=0.48, hspace=0.60)
    overview.savefig(args.output / "overview.png", dpi=240, facecolor=PAPER,
                     metadata={"Software": "plot.py"})
    overview.savefig(args.output / "overview.svg", facecolor=PAPER)
    plt.close(overview)
    print(f"Wrote {'overview' if args.overview_only else str(len(runs)) + ' run plots and overview'} to {args.output}")


if __name__ == "__main__":
    main()
