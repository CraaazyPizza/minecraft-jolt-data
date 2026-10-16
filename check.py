"""Verify dataset hashes and assigned hunger-jolt patterns with Java Random arithmetic."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MULTIPLIER = 0x5DEECE66D
MASK = (1 << 48) - 1


def pattern_at(tick, low_health=False):
    seed = (tick * 312871) & 0xFFFFFFFF
    if seed >= 1 << 31:
        seed -= 1 << 32
    state = (seed ^ MULTIPLIER) & MASK
    if low_health:
        for _ in range(10):
            state = (state * MULTIPLIER + 11) & MASK
    digits = []
    for _ in range(10):
        while True:
            state = (state * MULTIPLIER + 11) & MASK
            bits = state >> 17
            value = bits % 3
            if bits - value + 2 < 1 << 31:
                break
        digits.append("+0-"[value])
    return "".join(reversed(digits))


def main():
    index = json.loads((ROOT / "data/index.json").read_text())
    if sorted(run["rank"] for run in index["runs"]) != list(range(1, 101)):
        raise ValueError("Expected exactly 100 distinct leaderboard ranks")
    sources = {p["id"]: p for run in index["runs"] for p in run["proofs"]}
    assignments, candidates = 0, 0
    for proof in sources.values():
        payload = (ROOT / proof["data_file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != proof["data_sha256"]:
            raise ValueError(f"Data checksum mismatch: {proof['id']}")
        source = json.loads(payload)
        for observation in source["observations"]:
            for candidate in observation["candidates"]:
                tick = candidate["tick"]
                if tick % (observation["food"] * 3 + 1):
                    raise ValueError(f"Candidate food/tick mismatch: {proof['id']}, tick {tick}")
                if pattern_at(tick, candidate["low_health"]) != observation["pattern"]:
                    raise ValueError(f"Candidate pattern mismatch: {proof['id']}, tick {tick}")
                candidates += 1
        for segment in source["segments"]:
            for assignment in segment["assignments"]:
                observation = source["observations"][assignment["event_index"]]
                tick = assignment["tick"]
                if tick % (observation["food"] * 3 + 1):
                    raise ValueError(f"Food/tick mismatch: {proof['id']}, tick {tick}")
                if pattern_at(tick, assignment["low_health"]) != observation["pattern"]:
                    raise ValueError(f"Pattern mismatch: {proof['id']}, tick {tick}")
                if not any(c["tick"] == tick and c["low_health"] == assignment["low_health"]
                           for c in observation["candidates"]):
                    raise ValueError(f"Assignment absent from candidates: {proof['id']}, tick {tick}")
                assignments += 1
    print(f"Verified {len(sources)} source files, {candidates} candidate patterns and {assignments} assignments.")


if __name__ == "__main__":
    main()
