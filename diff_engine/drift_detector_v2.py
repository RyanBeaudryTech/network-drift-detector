import os
import json
from pathlib import Path

from diff_utils import (
    diff_dicts,
    format_diffs,
    save_diff,
    load_ignore_rules,
    filter_structured_diffs,
)

SNAPSHOT_DIR = "snapshots"
DIFF_DIR = "diffs"

# ------------------------------
# Load snapshots for a device
# ------------------------------
def load_snapshots(device):
    device_path = Path(SNAPSHOT_DIR) / device
    if not device_path.exists():
        return []
    return sorted(device_path.glob("*.json"))


# ------------------------------
# Load JSON snapshot file
# ------------------------------
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ------------------------------
# Main drift detector
# ------------------------------
def main():
    print("=== Network Drift Detector ===")

    # Load ignore rules
    rules = load_ignore_rules()  # looks for ignore_rules.json in project root

    for device in os.listdir(SNAPSHOT_DIR):
        device_path = Path(SNAPSHOT_DIR) / device
        if not device_path.is_dir():
            continue

        snapshots = load_snapshots(device)
        if len(snapshots) < 2:
            print(f"{device}: Not enough snapshots to compare.")
            continue

        previous = snapshots[-2]
        latest = snapshots[-1]

        print(f"\nComparing snapshots for {device}:")
        print(f"Previous: {previous.name}")
        print(f"Latest:   {latest.name}")

        prev_data = load_json(previous)
        new_data = load_json(latest)

        # Compute structured diffs
        diffs = diff_dicts(prev_data, new_data)


        # Filter diffs using ignore rules
        filtered_diffs = filter_structured_diffs(diffs, rules)

        if not filtered_diffs:
            print("✓ No drift detected")
            continue

        # Print human-readable filtered diff
        print(format_diffs(filtered_diffs))

        # Save filtered diff to disk
        save_diff(device, filtered_diffs)


# ------------------------------
# Entry point
# ------------------------------
if __name__ == "__main__":
    main()
