import json
import os
import difflib
from datetime import datetime

# =================================================
# 1. Recursive structured diff engine
# =================================================
def diff_dicts(old, new, path=""):
    """
    Recursively compares two Python data structures (dicts, lists, or values)
    and returns a list of structured diff records.

    Each diff record describes:
      - the JSON-style path where the change occurred
      - the type of change (added, removed, modified)
      - the old and/or new value involved

    This function is intentionally generic and data-agnostic so it can be
    reused for different snapshot formats (network data today, other systems later).
    """

    diffs = []

    # Case 1: Both values are dictionaries → compare keys recursively
    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        # Keys present only in the new snapshot
        for key in new_keys - old_keys:
            diffs.append({
                "path": f"{path}/{key}",
                "type": "added",
                "new": new[key]
            })

        # Keys present only in the old snapshot
        for key in old_keys - new_keys:
            diffs.append({
                "path": f"{path}/{key}",
                "type": "removed",
                "old": old[key]
            })

        # Keys present in both → recurse deeper
        for key in old_keys & new_keys:
            diffs.extend(
                diff_dicts(old[key], new[key], f"{path}/{key}")
            )

    # Case 2: Both values are lists → compare element-by-element
    elif isinstance(old, list) and isinstance(new, list):
        min_len = min(len(old), len(new))

        # Compare overlapping list elements
        for i in range(min_len):
            diffs.extend(
                diff_dicts(old[i], new[i], f"{path}[{i}]")
            )

        # Extra elements added in the new list
        for i in range(min_len, len(new)):
            diffs.append({
                "path": f"{path}[{i}]",
                "type": "added",
                "new": new[i]
            })

        # Elements removed from the old list
        for i in range(min_len, len(old)):
            diffs.append({
                "path": f"{path}[{i}]",
                "type": "removed",
                "old": old[i]
            })

    # Case 3: Primitive values (strings, numbers, etc.)
    else:
        if old != new:
            diffs.append({
                "path": path,
                "type": "modified",
                "old": old,
                "new": new
            })

    return diffs


# =================================================
# 2. Human-readable diff formatting
# =================================================
def format_diffs(diffs):
    """
    Converts structured diff records into a human-readable text format.

    This output is intended for:
      - console display
      - log files
      - basic audit review

    Note: This formatter is deliberately simple. More advanced formatting
    (e.g., section grouping or colorized output) can be layered on later.
    """

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


# =================================================
# 3. Persist structured diffs to disk
# =================================================
def save_diff(device, diffs):
    """
    Saves structured diffs to a timestamped JSON file.

    This provides:
      - historical auditability
      - the ability to re-process diffs later
      - separation between detection and reporting

    Files are organized per device for clarity.
    """

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
# 4. Load ignore rules configuration
# =================================================
def load_ignore_rules():
    """
    Loads ignore rules from ignore_rules.json.

    Ignore rules allow specific top-level snapshot paths (e.g. /routing_table)
    to be excluded from drift detection. This is useful for suppressing
    high-churn or low-signal data such as timestamps or packet counters.

    The file is loaded relative to this module to avoid dependency on
    the caller's working directory.
    """

    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, "ignore_rules.json")

        with open(file_path, "r") as f:
            raw = f.read()

            # Normalize values to strict booleans for predictable behavior
            rules = json.loads(raw)
            normalized = {key: bool(value) for key, value in rules.items()}

            return normalized

    except Exception as e:
        print(f"ERROR: Could not load ignore_rules.json: {e}")
        return {}


# =================================================
# 5. Apply ignore rules to structured diffs
# =================================================
def filter_structured_diffs(diffs, rules):
    """
    Filters structured diff records based on ignore rules.

    Parameters:
      diffs  - list of structured diff records produced by diff_dicts()
      rules  - dictionary mapping snapshot paths to boolean values

    Design choice:
      Ignore rules are applied AFTER diffs are generated.
      This preserves full visibility internally while allowing
      selective suppression of noise at reporting time.
    """

    filtered = []

    for entry in diffs:
        path = entry.get("path", "")

        # If a rule exists for this path and explicitly disables it, skip
        if path in rules and rules[path] is False:
            continue

        filtered.append(entry)

    return filtered
