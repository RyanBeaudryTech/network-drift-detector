import os
import json
from pathlib import Path
from deepdiff import DeepDiff

SNAPSHOT_DIR = "snapshots"

def load_snapshots(device):
    device_path = Path(SNAPSHOT_DIR) / device
    if not device_path.exists():
        return []

    snapshots = sorted(device_path.glob("*.json"))
    return snapshots

def compare_snapshots(file1, file2):
    with open(file1, "r") as f1, open(file2, "r") as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    diff = DeepDiff(data1, data2, ignore_order=True)
    return diff

def main():
    print("=== Network Drift Detector ===")

    for device in os.listdir(SNAPSHOT_DIR):
        device_path = Path(SNAPSHOT_DIR) / device
        if not device_path.is_dir():
            continue

        snapshots = load_snapshots(device)

        if len(snapshots) < 2:
            print(f"{device}: Not enough snapshots to compare.")
            continue

        # get latest two snapshots
        latest = snapshots[-1]
        previous = snapshots[-2]

        print(f"\nComparing snapshots for {device}:")
        print(f"Previous: {previous.name}")
        print(f"Latest:   {latest.name}")

        diff = compare_snapshots(previous, latest)

        if diff:
            print(f"⚠️ Drift detected on {device}:")
            print(diff)
        else:
            print(f"✓ No changes on {device}")

if __name__ == "__main__":
    main()
