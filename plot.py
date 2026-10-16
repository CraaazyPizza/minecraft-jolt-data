"""Regenerate the per-run plots and overview from the published JSON files."""

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

plt.switch_backend("Agg")

ROOT = Path(__file__).resolve().parent
GREEN = "#24644f"


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
    ax.tick_params(labelsize=5 if small else 9)
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
        ax.plot([lower, upper], [lower, upper], color="#bbbbbb", linewidth=0.7,
                linestyle="--", zorder=0, label="Equal elapsed time")
        for segment in segments:
            x, y = zip(*segment)
            ax.plot(x, y, color=GREEN, linewidth=0.45 if small else 0.7,
                    marker=".", markersize=1 if small else 2.5)
        ax.set_xlim(lower - padding, upper + padding)
        ax.set_ylim(lower - padding, upper + padding)
        ax.locator_params(axis="both", nbins=2 if small else 6)
    assert ax.get_xscale() == ax.get_yscale() == "linear"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "data/index.json")
    parser.add_argument("--output", type=Path, default=ROOT / "plots")
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    runs = sorted(index["runs"], key=lambda run: run["rank"])
    ranks = [run["rank"] for run in runs]
    if len(ranks) != len(set(ranks)):
        raise ValueError("Duplicate leaderboard ranks")
    args.output.mkdir(parents=True, exist_ok=True)
    overview, axes = plt.subplots(10, 10, figsize=(20, 21))
    overview.suptitle("Minecraft speedrun jolt clocks: top 100", fontsize=20, y=0.987)
    overview.text(0.5, 0.967, "Video elapsed (x) and GUI clock elapsed (y), in seconds. "
                  "Linear axes, equal scale. Dashed line: equal elapsed time.",
                  ha="center", fontsize=10)
    overview.text(0.5, 0.012, "Each proof starts at its first resolved jolt. "
                  "Gaps, menus and other attempts may be present. This is not a clean-run verdict.",
                  ha="center", fontsize=10)
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
        ax.set_title(f"#{rank}", fontsize=8, pad=2)
        if not run:
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
    overview.subplots_adjust(left=0.035, right=0.99, top=0.94, bottom=0.045,
                             wspace=0.45, hspace=0.55)
    overview.savefig(args.output / "overview.png", dpi=120, facecolor="white",
                     metadata={"Software": "plot.py"})
    plt.close(overview)
    print(f"Wrote {len(runs)} run plots and overview to {args.output}")


if __name__ == "__main__":
    main()
