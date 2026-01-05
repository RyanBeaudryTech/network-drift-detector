import os
import json
from pathlib import Path
from collections import defaultdict

from diff_utils_v2 import (
    diff_dicts,
    save_diff,
    load_ignore_rules,
    filter_structured_diffs,
    parse_routing_table, parse_arp_table, parse_interfaces_table,
    classify_severity
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

        # Preprocess ARP table
        if "arp_table" in prev_data:
            prev_data["arp_table"] = parse_arp_table(prev_data["arp_table"])

        if "arp_table" in new_data:
            new_data["arp_table"] = parse_arp_table(new_data["arp_table"])

        # Preprocess interface table
        if "interfaces" in prev_data:
            prev_data["interfaces"] = parse_interfaces_table(prev_data["interfaces"])

        if "interfaces" in new_data:
            new_data["interfaces"] = parse_interfaces_table(new_data["interfaces"])


        diffs = []

        # ---- Routing table (structured diff) ----
        if "routing_table" in prev_data and "routing_table" in new_data:
            route_diffs = diff_dicts(
                prev_data["routing_table"],
                new_data["routing_table"],
                path="/routing_table"
            )
            diffs.extend(route_diffs)

        # ---- ARP table (structured diff) ----
        if "arp_table" in prev_data and "arp_table" in new_data:
            arp_diffs = diff_dicts(
                prev_data["arp_table"],
                new_data["arp_table"],
                path="/arp_table"
            )
            diffs.extend(arp_diffs)

         # ---- interface table (structured diff) ----
        if "interfaces" in prev_data and "interfaces" in new_data:
            interface_diffs = diff_dicts(
                prev_data["interfaces"],
                new_data["interfaces"],
                path="/interfaces"
            )
            diffs.extend(interface_diffs)

        # Filter diffs using ignore rules
        filtered_diffs = filter_structured_diffs(diffs, rules)


        if not filtered_diffs:
            print("✓ No drift detected")
            continue

        # ------------------------------
        # Print human-readable filtered diff with text_diff for large strings
        # ------------------------------
        

        grouped = defaultdict(lambda: defaultdict(list))

        for change in filtered_diffs:
            severity = classify_severity(change)

            path = change.get("path", "")

            if path.startswith("/interfaces"):
                section = "Interfaces"
            elif path.startswith("/routing_table"):
                section = "Routing"
            elif path.startswith("/arp_table"):
                section = "ARP"
            else:
                section = "Other"

            grouped[severity][section].append(change)

        print("\n🔥 Drift Detected!\n")

        for severity in ("HIGH", "MEDIUM", "LOW"):
            if severity not in grouped:
                continue

            print(f"[{severity}]")
            print("=" * 40)

            for section, changes in grouped[severity].items():
                print(f"\n{section}")
                print("-" * 40)

                # ---------- COLLAPSED INTERFACE OUTPUT ----------
                if section == "Interfaces":
                    interfaces = defaultdict(dict)

                    # Collect changes first
                    for change in changes:
                        if change["type"] != "modified":
                            continue

                        path = change.get("path", "")
                        parts = path.strip("/").split("/")

                        # Expected: /interfaces/<iface>/<field>
                        if len(parts) < 3:
                            continue

                        iface = "/".join(parts[1:-1])
                        field = parts[-1]

                        interfaces[iface][field] = change

                    # Print once per interface
                    for iface, fields in interfaces.items():
                        details = []

                        # Admin state / status
                        if "admin_state" in fields:
                            c = fields["admin_state"]
                            old, new = c["old"], c["new"]
                            # Only collapse when new state is admin shutdown
                            if str(new).lower().startswith("administratively") and old != new:
                                details.append("administratively down")
                            else:
                                details.append(f"admin {old} → {new}")
                        elif "status" in fields:
                            c = fields["status"]
                            details.append(f"admin {c['old']} → {c['new']}")

                        # Operational state / protocol
                        if "oper_state" in fields:
                            c = fields["oper_state"]
                            old, new = c["old"], c["new"]
                            if not any("administratively" in d.lower() for d in details):
                                if old != new:
                                    details.append(f"oper {old} → {new}")
                        elif "protocol" in fields:
                            c = fields["protocol"]
                            old, new = c["old"], c["new"]
                            if not any("administratively" in d.lower() for d in details):
                                if old != new:
                                    details.append(f"oper {old} → {new}")

                        if details:
                            print(f"* {iface}: " + ", ".join(details))

                    continue  # skip per-change printing




                # ---------- NON-INTERFACE SECTIONS ----------
                for change in changes:
                    change_type = change["type"]
                    old = change.get("old")
                    new = change.get("new")

                    if section == "ARP":
                        if change_type == "added":
                            print(f"+ ARP {new['mac']} on {new['interface']}")
                        elif change_type == "removed":
                            print(f"- ARP {old['mac']} on {old['interface']}")
                    else:
                        if change_type == "added":
                            print(f"+ {new}")
                        elif change_type == "removed":
                            print(f"- {old}")
                        elif change_type == "modified":
                            print(f"* {old} → {new}")




            print("")



        # Save filtered diff to disk
        save_diff(device, filtered_diffs)


if __name__ == "__main__":
    main()
