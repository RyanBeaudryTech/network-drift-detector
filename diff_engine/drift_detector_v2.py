import os
import json
from pathlib import Path

from diff_utils_v2 import (
    diff_dicts,
    save_diff,
    load_ignore_rules,
    filter_structured_diffs,
    text_diff,
    parse_routing_table
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


        # Preprocess routing table into structured dicts
        if "routing_table" in prev_data:
            prev_data["routing_table"] = parse_routing_table(prev_data["routing_table"])

        if "routing_table" in new_data:
            new_data["routing_table"] = parse_routing_table(new_data["routing_table"])

      
        #diffs = diff_dicts(prev_data, new_data)
        diffs = []

        # ---- Routing table (structured diff) ----
        if "routing_table" in prev_data and "routing_table" in new_data:
            route_diffs = diff_dicts(
                prev_data["routing_table"],
                new_data["routing_table"],
                path="/routing_table"
            )
            diffs.extend(route_diffs)



        # Filter diffs using ignore rules
        filtered_diffs = filter_structured_diffs(diffs, rules)

        if not filtered_diffs:
            print("✓ No drift detected")
            continue

        # ------------------------------
        # Print human-readable filtered diff with text_diff for large strings
        # ------------------------------
        for change in filtered_diffs:
            path = change.get("path", "")
            change_type = change.get("type")

            print(f"--- {path} ---")

            if change_type == "added":
                print(f"Added: {change['new']}\n")
            elif change_type == "removed":
                print(f"Removed: {change['old']}\n")
            elif change_type == "modified":
                old_val = change.get("old")
                new_val = change.get("new")

                # If both old and new are strings, use text_diff
                if isinstance(old_val, str) and isinstance(new_val, str):
                    print(text_diff(old_val, new_val))
                else:
                    # For non-string values, just print normally
                    print(f"Old: {old_val}")
                    print(f"New: {new_val}\n")
                

        # Save filtered diff to disk
        save_diff(device, filtered_diffs)

        #DEBUG
        #break


# ------------------------------
# Entry point
# ------------------------------
if __name__ == "__main__":
    main()
