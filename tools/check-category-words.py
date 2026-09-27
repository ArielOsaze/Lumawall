"""Check the category word lists for words that belong to more than one category.

Why: "skyline" was in the Cars list as a Nissan model and in the City list as a city horizon.
The classifier tries Cars before City, so every city skyline wallpaper was filed under Cars -
79 of them. "dragon" sat in Animals and Fantasy, "butterfly" in Animals and Nature. A word in
two lists is not a small untidiness: it silently moves entries, and the move is invisible in
the category counts because the total stays the same.

This reads the lists out of the classifier and reports every overlap, so the precedence can
be a decision rather than an accident.

Run: python tools/check-category-words.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "recategorise.py"


def load_lists():
    """Every module-level set of category words, as {category: set}.

    Comments are stripped first. Without that the loader reads the notes as data: the line
    `#   "skyline" - also a city horizon` put the word straight back into the Cars list and
    the checker reported an overlap that the code no longer had. A checker that reads its own
    explanations as facts is worse than no checker, because it reports a fault that is not
    there and hides the ones that are.
    """
    text = SOURCE.read_text(encoding="utf-8")

    # Drop whole-line comments and trailing comments, but not a '#' inside a string.
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # A trailing comment: a '#' that is not inside quotes.
        in_string = False
        cut = None
        for i, ch in enumerate(line):
            if ch == '"':
                in_string = not in_string
            elif ch == "#" and not in_string:
                cut = i
                break
        lines.append(line[:cut] if cut is not None else line)
    text = "\n".join(lines)

    lists = {}
    for match in re.finditer(r"^([A-Z][A-Z_]*)\s*=\s*\{(.*?)^\}", text, re.S | re.M):
        name = match.group(1)
        body = match.group(2)
        if name in ("ORDER",):
            continue
        words = set()
        for literal in re.findall(r'"([^"]+)"', body):
            words.add(literal.lower())
        if words:
            lists[name] = words
    return lists


# Sets that describe an entry rather than compete for it. GIRL_MARKERS is a marker used
# inside the anime rule, and MATURE is the justification list - neither is a category that
# an entry is filed under, so a word appearing in one of them and in a category is not the
# silent move this check is looking for.
NOT_CATEGORIES = {"GIRL_MARKERS", "MATURE"}


def main():
    if not SOURCE.exists():
        print("  %s is missing" % SOURCE)
        return 1

    lists = load_lists()
    print("  %d word lists" % len(lists))
    for name, words in sorted(lists.items()):
        print("    %-12s %4d words" % (name, len(words)))
    print()

    # Every word that appears in more than one category list.
    owners = {}
    for name, words in lists.items():
        if name in NOT_CATEGORIES:
            continue
        for word in words:
            owners.setdefault(word, set()).add(name)

    shared = {w: names for w, names in owners.items() if len(names) > 1}

    if not shared:
        print("  OK    no word belongs to two categories.")
        return 0

    print("  %d word(s) belong to more than one category:" % len(shared))
    print()
    for word, names in sorted(shared.items()):
        print("    %-18s %s" % (word, ", ".join(sorted(names))))

    print()
    print("  Each of these silently moves entries from the later category to the earlier one.")
    print("  Either remove the word from the list that should not have it, or accept the")
    print("  precedence and say so in a comment beside it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
