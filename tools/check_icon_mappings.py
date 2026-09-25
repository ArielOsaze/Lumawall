"""Cross-checks that every icon glyph the UI asks for has an explicit mapping.

The window-control bug happened because `\\uE921` (minimize) and `\\uE922`
(maximize) were used in the title bar but absent from IconNameFor(), so both
silently fell through to the `default` icon and rendered identically. This
script makes that class of bug visible instead of relying on someone noticing.

In the C# source the codes appear as the two characters backslash + 'u' followed
by four hex digits, so the patterns below match a single literal backslash.
"""
import os
import re

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "LumaWall", "MainWindow.cs")

with open(SRC, encoding="utf-8") as fh:
    source = fh.read()

CODE = r"\\u[0-9A-Fa-f]{4}"          # backslash + u + 4 hex digits

# Codes the UI requests: Glyph("\uXXXX") and TitleButton("\uXXXX")
used = set(re.findall(r'(?:Glyph|TitleButton)\("(' + CODE + r')"', source))
# Codes that have an explicit icon: case "\uXXXX":
mapped = set(re.findall(r'case "(' + CODE + r')":', source))

print("glyph codes used   : %d" % len(used))
print("glyph codes mapped : %d" % len(mapped))
print()

missing = sorted(used - mapped)
unused = sorted(mapped - used)

if missing:
    print("UNMAPPED (falls back to the default icon):")
    for code in missing:
        print("   " + code)
else:
    print("OK: every glyph the UI uses has an explicit icon mapping.")

if unused:
    print()
    print("Mapped but unused (harmless):")
    for code in unused:
        print("   " + code)

raise SystemExit(1 if missing else 0)
