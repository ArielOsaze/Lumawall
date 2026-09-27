"""Record which mature candidates were kept by the visual review.

Why: 756 candidates were rendered as contact sheets and looked at, and 249 were kept. The
selection lived inside a PowerShell script as a literal list of indices, which meant the
review could not be reused by anything else - and when the catalogue was rebuilt, the mature
category collapsed to 3 entries because the new pipeline had no way to read the review.

This reads that list once and writes mature-audit/selected.json, which the merge step
consumes. The indices are taken from the script rather than retyped, so the two cannot drift.

Run: python tools/export-mature-selection.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json

SCRIPT = ROOT / "apply_mature_audit.ps1"
CANDIDATES = ROOT / "mature-audit" / "candidates.json"
OUT = ROOT / "mature-audit" / "selected.json"


def main():
    if not SCRIPT.exists():
        print("  %s is missing" % SCRIPT)
        return 1
    if not CANDIDATES.exists():
        print("  %s is missing" % CANDIDATES)
        return 1

    script = SCRIPT.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\$selectedText\s*=\s*'([0-9,\s]+)'", script)
    if not m:
        print("  cannot find the selected index list in %s" % SCRIPT.name)
        return 1

    indices = [int(x) for x in m.group(1).replace(" ", "").split(",") if x]
    print("  %d indices in the audit script" % len(indices))

    candidates = read_json(CANDIDATES, [])
    by_index = {c.get("auditIndex"): c for c in candidates}
    print("  %d candidates in the sheet" % len(candidates))
    print()

    selected = []
    missing = []
    for index in indices:
        c = by_index.get(index)
        if not c:
            missing.append(index)
            continue
        selected.append({
            "motionId": str(c.get("motionId", "")),
            "title": c.get("title", ""),
            "auditIndex": index,
        })

    if missing:
        print("  FAIL  %d index/indices are not in the candidate sheet: %s"
              % (len(missing), missing[:10]))
        return 1

    write_json(OUT, selected)

    print("  selected : %d" % len(selected))
    print("  written  : %s" % OUT)
    print()
    print("  a sample:")
    for s in selected[:6]:
        print("    %-46s id=%s" % (s["title"][:46], s["motionId"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
