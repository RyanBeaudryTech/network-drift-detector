import json
import os
import difflib
from datetime import datetime

# Keys whose values should be diffed as raw text (line-by-line)
TEXT_DIFF_KEYS = {
    "routing_table",
    "arp_table",
    "interfaces"
}

# -------------------------------------------------
# Snapshot splitting (TEXT vs STRUCTURED)
# -------------------------------------------------

def split_snapshot(snapshot):
    """
    Splits a snapshot dictionary into:
    - text_sections: keys whose values should be diffed line-by-line
    - structured_sections: everything else
    """
    text_sections = {}
    structured_sections = {}

    for key, value in snapshot.items():
        if key in TEXT_DIFF_KEYS and isinstance(value, str):
            text_sections[key] = value
        else:
            structured_sections[key] = value

    return text_sections, structured_sections


# -------------------------------------------------
# Helper: Line-by-line unified diff for large text blocks
# -------------------------------------------------
def text_diff(old, new):
    """
    Generate a line-by-line unified diff between old and new strings.

    Args:
        old (str): old multi-line text
        new (str): new multi-line text

    Returns:
        str: formatted diff string
    """
    old_lines = old.splitlines() if old else []
    new_lines = new.splitlines() if new else []

    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='old',
        tofile='new',
        lineterm=''  # prevents extra newlines
    ))

    return "\n".join(diff_lines) if diff_lines else "No changes in text content."




# =================================================
# Recursive structured diff engine
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
# Human-readable diff formatting
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
        path = change["path"]
        output.append(f"--- {path} ---")

        if change["type"] == "added":
            output.append(f"Added: {change['new']}\n")
        elif change["type"] == "removed":
            output.append(f"Removed: {change['old']}\n")
        elif change["type"] == "modified":
            # Use line-by-line diff for large text blocks
            if path in LINE_BY_LINE_PATHS and isinstance(change["old"], str) and isinstance(change["new"], str):
                output.append(text_diff(change["old"], change["new"]))
                output.append("")  # extra newline
            else:
                output.append(f"Old: {change['old']}")
                output.append(f"New: {change['new']}\n")

    return "\n".join(output)


# =================================================
# Persist structured diffs to disk
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
# Load ignore rules configuration
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
# Apply ignore rules to structured diffs
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
