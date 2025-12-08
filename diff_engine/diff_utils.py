import json
import os
import difflib
from datetime import datetime

# -------------------------------------------------
# 1. Recursive structured diff (your original)
# -------------------------------------------------
def diff_dicts(old, new, path=""):
    diffs = []

    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for key in new_keys - old_keys:
            diffs.append({
                "path": f"{path}/{key}",
                "type": "added",
                "new": new[key]
            })

        for key in old_keys - new_keys:
            diffs.append({
                "path": f"{path}/{key}",
                "type": "removed",
                "old": old[key]
            })

        for key in old_keys & new_keys:
            diffs.extend(
                diff_dicts(old[key], new[key], f"{path}/{key}")
            )

    elif isinstance(old, list) and isinstance(new, list):
        min_len = min(len(old), len(new))
        for i in range(min_len):
            diffs.extend(
                diff_dicts(old[i], new[i], f"{path}[{i}]")
            )

        for i in range(min_len, len(new)):
            diffs.append({
                "path": f"{path}[{i}]",
                "type": "added",
                "new": new[i]
            })

        for i in range(min_len, len(old)):
            diffs.append({
                "path": f"{path}[{i}]",
                "type": "removed",
                "old": old[i]
            })

    else:
        if old != new:
            diffs.append({
                "path": path,
                "type": "modified",
                "old": old,
                "new": new
            })

    return diffs


# -------------------------------------------------
# 2. Human-readable formatting
# -------------------------------------------------
def format_diffs(diffs):
    if not diffs:
        return "No drift detected.\n"

    output = ["\n🔥 Drift Detected!\n"]

    for change in diffs:
        output.append(f"--- {change['path']} ---")

        if change["type"] == "added":
            output.append(f"Added: {change['new']}\n")
        elif change["type"] == "removed":
            output.append(f"Removed: {change['old']}\n")
        else:
            output.append(f"Old: {change['old']}")
            output.append(f"New: {change['new']}\n")

    return "\n".join(output)


# -------------------------------------------------
# 3. Save structured diff as JSON
# -------------------------------------------------
def save_diff(device, diffs):
    if not diffs:
        return None

    diff_dir = os.path.join("diffs", device)
    os.makedirs(diff_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(diff_dir, f"diff_{timestamp}.json")

    with open(filename, "w") as f:
        json.dump(diffs, f, indent=2)

    return filename


# =================================================
# NEW SECTION — FILTERING LOGIC (missing before)
# =================================================

# -------------------------------------------------
# 4. Load ignore rules (keys, values, substrings)
# -------------------------------------------------

def load_ignore_rules():

    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, "ignore_rules.json")

        with open(file_path, "r") as f:
            raw = f.read()
            print(f"DEBUG: Raw file contents:\n{raw}")

            rules = json.loads(raw)
            normalized = {key: bool(value) for key, value in rules.items()}

            print(f"DEBUG: Normalized rules: {normalized}")
            return normalized

    except Exception as e:
        print(f"ERROR: Could not load ignore_rules.json: {e}")
        return {}





# -------------------------------------------------
# 5. Filter recursive structured diffs
# -------------------------------------------------
def filter_structured_diffs(diffs, rules):
    """
    diffs: list of {"path": "/something", "type": "...", "old": "...", "new": "..."}
    rules: dict like {"/routing_table": false}
    """

    filtered = []

    for entry in diffs:
        path = entry.get("path", "")

        # If rules explicitly ignore this top-level path
        if path in rules:
            if rules[path] is False:
                # Skip this diff entirely
                continue

        filtered.append(entry)

    return filtered



# -------------------------------------------------
# 6. Unified diff generator (raw text diff)
# -------------------------------------------------
def unified_json_diff(old_json, new_json):
    old_lines = json.dumps(old_json, indent=2).splitlines()
    new_lines = json.dumps(new_json, indent=2).splitlines()

    return list(difflib.unified_diff(
        old_lines, new_lines, lineterm=""
    ))


# -------------------------------------------------
# 7. Filter unified (text) diffs
# -------------------------------------------------
def filter_unified_diff(diff_lines, rules):
    ignore_words = rules.get("ignore_lines_containing", [])
    ignore_keys = rules.get("ignore_keys", [])

    filtered = []
    for line in diff_lines:
        if any(word in line for word in ignore_words):
            continue
        if any(f'"{key}"' in line for key in ignore_keys):
            continue
        filtered.append(line)

    return filtered
