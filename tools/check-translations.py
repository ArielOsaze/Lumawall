"""Every translation key the UI asks for must exist in the dictionary.

This exists because it did not, and the result was a page that rendered as raw
keys: a slider labelled "studio.brightness", a shape button labelled "timer.pill",
the nav rail labelled "nav.studio". Tr() falls back to returning the key when it
is missing, which is a reasonable runtime choice - it keeps a typo from throwing -
but it means a missing key is invisible to the compiler, invisible in the log, and
visible only to a user reading the screen.

Checks, in order of how badly each one breaks the app:

  1. Every key used in a Tr("...") call exists in the dictionary.
  2. Every entry has exactly four languages. Tr() indexes by language, so a
     three-language entry throws IndexOutOfRange on Chinese or Japanese.
  3. Entries defined but never used are reported, not failed - dead copy
     accumulates and makes the dictionary hard to audit.

Run it from the repository root: python tools/check-translations.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "LumaWall" / "MainWindow.cs"

# Languages the app ships, in the order the dictionary stores them.
LANGUAGES = ["id", "en", "zh", "ja"]


def read(path):
    """Read C# source as UTF-8, tolerating a byte-order mark."""
    return path.read_bytes().decode("utf-8-sig")


def dictionary_entries(text):
    """Parse the Copy initialiser into {key: [values]}.

    A regex over `new[] { ... }` is not enough here: some entries contain a literal
    `{0}` placeholder, and a pattern that stops at the first `}` silently truncates
    them to one language - which is exactly the shape of the bug this file checks
    for, so a parser that can produce it would be worse than none. This walks the
    string literals instead.
    """
    start = text.find("new Dictionary<string, string[]>")
    if start < 0:
        raise SystemExit("  ERROR: cannot find the Copy dictionary in %s" % SOURCE.name)

    # The dictionary ends at the first closing brace at the same indent level.
    end = text.find("\n        };", start)
    if end < 0:
        raise SystemExit("  ERROR: cannot find the end of the Copy dictionary")
    body = text[start:end]

    entries = {}
    pattern = re.compile(r'\{\s*"([A-Za-z][A-Za-z0-9._]*)"\s*,\s*new\[\]\s*\{')
    literal = re.compile(r'\s*"((?:[^"\\]|\\.)*)"\s*(,?)')

    pos = 0
    while True:
        match = pattern.search(body, pos)
        if not match:
            break
        key = match.group(1)
        cursor = match.end()

        values = []
        while True:
            item = literal.match(body, cursor)
            if not item:
                break
            values.append(item.group(1))
            cursor = item.end()
            if not item.group(2):
                break

        entries[key] = values
        pos = cursor

    return entries


def used_keys():
    """Every key passed to Tr("...") anywhere in the app, with its file."""
    used = {}
    for path in sorted((ROOT / "LumaWall").rglob("*.cs")):
        if "obj" in path.parts or "bin" in path.parts:
            continue
        text = read(path)
        for key in re.findall(r'Tr\("([A-Za-z][A-Za-z0-9._]*)"\)', text):
            used.setdefault(key, set()).add(path.name)
    return used


def main():
    text = read(SOURCE)
    entries = dictionary_entries(text)
    used = used_keys()

    print("  dictionary entries : %d" % len(entries))
    print("  keys used in code  : %d" % len(used))
    print()

    failures = 0

    # 1. missing keys
    missing = sorted(k for k in used if k not in entries)
    if missing:
        failures += len(missing)
        print("  FAIL  %d key(s) used but not in the dictionary." % len(missing))
        print("        Tr() returns the key itself, so each of these renders as")
        print("        raw text in the UI:")
        for key in missing:
            print("          %-28s %s" % (key, ", ".join(sorted(used[key]))))
        print()

    # 2. wrong language count
    wrong = sorted((k, len(v)) for k, v in entries.items() if len(v) != len(LANGUAGES))
    if wrong:
        failures += len(wrong)
        print("  FAIL  %d entry/entries do not have four languages." % len(wrong))
        print("        Tr() indexes by language, so these throw on a switch to")
        print("        Chinese or Japanese:")
        for key, count in wrong:
            print("          %-28s %d language(s)" % (key, count))
        print()

    # 3. dead entries - reported, not counted as a failure
    dead = sorted(k for k in entries if k not in used)
    if dead:
        print("  NOTE  %d entr(ies) defined but never used:" % len(dead))
        for key in dead[:20]:
            print("          %s" % key)
        if len(dead) > 20:
            print("          ... and %d more" % (len(dead) - 20))
        print()

    if failures:
        print("  %d problem(s) found." % failures)
        return 1

    print("  OK    every key the UI asks for is present, with four languages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
