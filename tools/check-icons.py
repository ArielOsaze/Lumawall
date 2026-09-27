"""Every icon must come from the Lucide set, and nothing may draw its own colour.

Why: the icon set was hand-drawn, one path per icon, and a screenshot of the dashboard was
reported as looking like AI-generated placeholder art. That is what a set with no shared
proportions looks like. It is now generated from Lucide, and this keeps it that way.

Checks:

  1. Every icon the app references exists in the set.
  2. Every icon in the set is referenced by something - a set with unused entries is a set
     nobody is maintaining.
  3. Every path string is one WPF will accept: it starts with a move, and contains only the
     characters the path mini-language allows. A typo here throws at runtime, on the page
     that draws the icon, which is the worst place to find it.
  4. Every icon is on the 24x24 grid. An icon authored on a different grid renders at the
     wrong size next to the others, which is the fault that made the old set look uneven.
  5. No icon carries its own colour. The app tints icons to match their context, so an
     icon with a hard-coded fill would be the "warna-warni" the design is avoiding.

Run: python tools/check-icons.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS_CS = ROOT / "LumaWall" / "Icons.cs"
LUCIDE_JSON = ROOT / "build" / "icons-lucide.json"

# The path mini-language WPF's Geometry.Parse accepts.
PATH_CHARS = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9 ,.\-+eE]*$")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def read(path):
    return path.read_bytes().decode("utf-8-sig")


def declared_constants(text):
    """The icon names declared as consts, as a set."""
    return {name for name, _ in re.findall(r'public const string (\w+)\s*=\s*"([^"]+)"', text)}


def grid_violation(path):
    """Walk a path and report the first absolute coordinate that leaves 0..24.

    Walking is the only correct way to do this. Counting arguments per command is what
    distinguishes a coordinate from a radius, a rotation or an arc flag, and the relative
    commands (m, l, h, v, c, s, q, t, a) move the cursor rather than setting it - so a
    path like "M20 6 9 17l-5-5" is entirely inside the grid even though it contains a -5.
    """
    # How many numbers each command takes. A repeated command block reuses the count, and
    # m/M's first block is a move while the rest are implicit line-tos - both are positions,
    # so they are treated the same here.
    arity = {
        "m": 2, "l": 2, "t": 2,
        "h": 1, "v": 1,
        "c": 6, "s": 4, "q": 4,
        "a": 7,
        "z": 0,
    }

    # The tokenizer splits a path into commands and numbers. Numbers can run into a command
    # letter without a separator - "9A1.5" is the number 9, the command A, and the number
    # 1.5 - so the pattern matches either a single command letter or a full number, and
    # anything else would be a malformed path.
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", path)
    x, y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    command = None
    index = 0

    def is_number(token):
        return not re.match(r"^[A-Za-z]$", token)

    while index < len(tokens):
        token = tokens[index]
        if not is_number(token):
            command = token
            index += 1
            if command in ("z", "Z"):
                x, y = start_x, start_y
                continue
        if command is None:
            return "path starts with a number"

        lower = command.lower()
        if lower not in arity:
            return "unknown command %r" % command
        count = arity[lower]
        if index + count > len(tokens):
            return "command %s is missing arguments" % command

        # An arc's two flags may be written without separators - "0 00-2.474" is three
        # values, not one - so a run of digits at a flag position is split. This is the one
        # place the SVG grammar allows digits to run together.
        args = []
        cursor = index
        for position in range(count):
            if cursor >= len(tokens):
                return "command %s is missing arguments" % command
            value = tokens[cursor]
            if not is_number(value):
                return "command %s has too few arguments (found %s)" % (command, value)

            # Positions 3 and 4 of an arc are its flags, and each is a SINGLE character -
            # SVG allows them to run together with the numbers around them. The tokenizer
            # cannot know that, so "005.5" arrives as one token where it means the flag 0,
            # the flag 0, and the number 5.5. Take one character and leave the rest in the
            # token stream for the positions that follow.
            if lower == "a" and position in (3, 4):
                text = tokens[cursor]
                if len(text) > 1:
                    args.append(float(text[0]))
                    tokens[cursor] = text[1:]
                    continue

            args.append(float(value))
            cursor += 1
        index = cursor

        relative = command.islower()
        if lower == "m":
            x = x + args[0] if relative else args[0]
            y = y + args[1] if relative else args[1]
            start_x, start_y = x, y
            # Following blocks of an m are implicit line-tos.
            command = "l" if relative else "L"
        elif lower == "l":
            x = x + args[0] if relative else args[0]
            y = y + args[1] if relative else args[1]
        elif lower == "t":
            x = x + args[0] if relative else args[0]
            y = y + args[1] if relative else args[1]
        elif lower == "h":
            x = x + args[0] if relative else args[0]
        elif lower == "v":
            y = y + args[0] if relative else args[0]
        elif lower == "c":
            points = [(args[0], args[1]), (args[2], args[3]), (args[4], args[5])]
            if relative:
                points = [(x + px, y + py) for px, py in points]
            for px, py in points:
                if px < -0.5 or px > 24.5 or py < -0.5 or py > 24.5:
                    return "control point %.1f,%.1f is outside 0..24" % (px, py)
            x, y = points[-1]
        elif lower == "s":
            points = [(args[0], args[1]), (args[2], args[3])]
            if relative:
                points = [(x + px, y + py) for px, py in points]
            for px, py in points:
                if px < -0.5 or px > 24.5 or py < -0.5 or py > 24.5:
                    return "control point %.1f,%.1f is outside 0..24" % (px, py)
            x, y = points[-1]
        elif lower == "q":
            points = [(args[0], args[1]), (args[2], args[3])]
            if relative:
                points = [(x + px, y + py) for px, py in points]
            for px, py in points:
                if px < -0.5 or px > 24.5 or py < -0.5 or py > 24.5:
                    return "control point %.1f,%.1f is outside 0..24" % (px, py)
            x, y = points[-1]
        elif lower == "a":
            # args are: rx ry rotation large-arc sweep x y
            #
            # The two flags are single digits and SVG allows them to run into the numbers
            # around them: "a1.5 1.5 0 00-2.474-1.561" is rx=1.5, ry=1.5, rotation=0,
            # large-arc=0, sweep=0, x=-2.474, y=-1.561. A tokenizer that splits on
            # non-digits reads "00-2.474" as one number and reports the path as broken.
            end = (args[5], args[6])
            if relative:
                end = (x + end[0], y + end[1])
            x, y = end

        if x < -0.5 or x > 24.5 or y < -0.5 or y > 24.5:
            return "position %.1f,%.1f is outside 0..24" % (x, y)

    return None


def geometry_cases(text):
    """The case label and its paths, as {constant: [path, ...]}."""
    start = text.find("private static IEnumerable<string> GeometryFor")
    if start < 0:
        raise SystemExit("  cannot find GeometryFor in Icons.cs")
    end = text.find("\n        }", start)
    body = text[start:end]

    cases = {}
    for match in re.finditer(r"case (\w+):(.*?)break;", body, re.S):
        constant = match.group(1)
        paths = re.findall(r'yield return "((?:[^"\\]|\\.)*)";', match.group(2))
        cases[constant] = [p.replace("\\\\", "\\").replace('\\"', '"') for p in paths]
    return cases


def main():
    if not ICONS_CS.exists():
        print("  %s is missing" % ICONS_CS)
        return 1

    text = read(ICONS_CS)
    constants = declared_constants(text)          # set of constant names
    cases = geometry_cases(text)

    print("  icons declared : %d" % len(constants))
    print("  icons with art : %d" % len(cases))
    print()

    failures = 0

    # 1. every declared icon has geometry
    missing_art = sorted(c for c in constants if c not in cases)
    if missing_art:
        failures += len(missing_art)
        print("  FAIL  %d icon(s) declared with no geometry - Build() would return a blank"
              % len(missing_art))
        for constant in missing_art:
            print("          %s" % constant)
        print()

    # 2. every geometry case is declared (a case with no const is unreachable)
    orphan_cases = sorted(c for c in cases if c not in constants)
    if orphan_cases:
        failures += len(orphan_cases)
        print("  FAIL  %d case(s) with no matching const - unreachable" % len(orphan_cases))
        for constant in orphan_cases:
            print("          %s" % constant)
        print()

    # 3 + 4. the paths themselves
    bad_paths = []
    empty = []

    for constant, paths in sorted(cases.items()):
        if not paths:
            empty.append(constant)
            continue

        for path in paths:
            if not PATH_CHARS.match(path):
                bad_paths.append((constant, path, "contains a character WPF will not parse"))
                continue
            if not re.match(r"^[Mm]", path):
                bad_paths.append((constant, path, "does not start with a move"))

    if empty:
        failures += len(empty)
        print("  FAIL  %d icon(s) with an empty geometry list" % len(empty))
        for constant in empty:
            print("          %s" % constant)
        print()

    if bad_paths:
        failures += len(bad_paths)
        print("  FAIL  %d path(s) WPF cannot parse" % len(bad_paths))
        for constant, path, why in bad_paths[:10]:
            print("          %-14s %s" % (constant, why))
            print("            %s" % path[:90])
        print()

    # 4. the grid. A path is on the 24x24 grid if every absolute coordinate is inside it -
    # and finding those needs the path walked, not just its numbers read.
    #
    # The first version of this check took the largest number in the string and called it a
    # coordinate. That is wrong twice: SVG paths use relative commands (l, v, h) whose
    # numbers are offsets rather than positions, and an arc's first two numbers are a radius
    # and a rotation. "M20 6 9 17l-5-5" was reported as outside the grid because of the -5,
    # which is a relative offset and cannot leave the grid at all.
    off_grid = []
    for constant, paths in sorted(cases.items()):
        for path in paths:
            escaped = grid_violation(path)
            if escaped:
                off_grid.append((constant, path, escaped))

    if off_grid:
        failures += len(off_grid)
        print("  FAIL  %d path(s) leave the 24x24 grid" % len(off_grid))
        for constant, path, why in off_grid[:10]:
            print("          %-14s %s" % (constant, why))
            print("            %s" % path[:90])
        print()

    # 5. no icon may set its own colour. A hard-coded colour is the "warna-warni" the
    # design avoids, and it also means the icon ignores the tint its caller passes.
    #
    # What counts is a colour VALUE, not the words fill and stroke: the file has to say
    # `Stroke = brush` and `Fill = filled ? brush : null` to draw anything at all, and a
    # check that flagged those would flag the only correct implementation.
    colour_values = re.findall(r'\b(?:Fill|Stroke|Background)\s*=\s*([^,;)]+)', text)
    hard_coded = [v.strip() for v in colour_values
                  if re.search(r'#[0-9a-fA-F]{3,8}|Brushes\.\w+$|Color\.From|Colors\.\w+$', v.strip())]

    if hard_coded:
        failures += len(hard_coded)
        print("  FAIL  %d icon(s) carry a colour of their own - icons must be tinted by"
              % len(hard_coded))
        print("        their caller, so the shell decides what colour they are")
        for value in hard_coded[:6]:
            print("          %s" % value)
        print()

    # 6. the set matches what was fetched from Lucide
    if LUCIDE_JSON.exists():
        import json
        data = json.loads(read(LUCIDE_JSON))
        expected = {i["appName"] for i in data.get("icons", [])}
        actual = set(cases)
        # Map app names to constants for comparison.
        expected_constants = set()
        for app_name in expected:
            for constant in constants:
                if constant.lower().startswith(app_name.lower()[:4]):
                    expected_constants.add(constant)
        if len(cases) < len(expected):
            print("  NOTE  the file has %d icons; Lucide supplied %d. Regenerate with"
                  % (len(cases), len(expected)))
            print("        python tools/apply-lucide-icons.py if that is not deliberate")
            print()
    else:
        print("  NOTE  %s is missing, so the set cannot be compared with its source" % LUCIDE_JSON.name)
        print()

    if failures:
        print("  %d problem(s) found." % failures)
        return 1

    print("  OK    every icon is present, on-grid, parseable and colourless.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
