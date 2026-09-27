"""Prove the icon test can fail.

Why this exists: the icon test reported success against a build that had not compiled. The
injected fault referenced a variable declared after its use, so the compiler refused the
file, the previous LumaWall.exe was still on disk, and the test loaded that and passed. A
test that passes when the code does not build is worse than no test - it says "verified"
about something nobody checked.

This script is the check on the check: it breaks the icon builder in a way that compiles,
and requires the test to fail.

Run: python tools/verify-icon-test-fails.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "LumaWall" / "Icons.cs"
BACKUP = ROOT / "build" / "Icons.cs.good"

# A fault that compiles: the scale is computed from the size the method already has, so
# nothing is used before it is declared. It reproduces the real crash - Geometry.Parse
# hands back a read-only geometry, and assigning Transform to it throws at runtime, inside
# the window's construction.
BROKEN_HELPER = """        private static Geometry ReadOnly(string data, double size)
        {
            // Deliberately wrong: Geometry.Parse returns a geometry that is already frozen,
            // and a frozen Freezable refuses a new Transform. This is the exact fault that
            // stopped the window from opening.
            var geometry = Geometry.Parse(data);
            geometry.Transform = new ScaleTransform(size / Grid, size / Grid);
            return geometry;
        }

        private static IEnumerable<string> GeometryFor(string name)"""


def build():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", "tools/build_app.ps1"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    output = result.stdout + result.stderr
    if "build OK" not in output:
        print("  the build did not report success:")
        for line in output.strip().splitlines()[-12:]:
            print("    %s" % line)
        return False
    return True


def main():
    if not ICONS.exists():
        print("  %s is missing" % ICONS)
        return 1

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_bytes(ICONS.read_bytes())

    try:
        text = ICONS.read_text(encoding="utf-8")
        if "                    Data = Geometry.Parse(data)," not in text:
            print("  cannot find the geometry assignment - the test needs updating")
            return 1

        broken = text.replace(
            "                    Data = Geometry.Parse(data),",
            "                    Data = ReadOnly(data, size),",
        ).replace(
            "        private static IEnumerable<string> GeometryFor(string name)",
            BROKEN_HELPER,
        )
        ICONS.write_text(broken, encoding="utf-8")

        print("  broke the icon builder on purpose")
        if not build():
            print()
            print("  FAIL  the broken version does not compile, so this check cannot tell")
            print("        whether the test would have caught the fault")
            return 1
        print("  the broken version compiles")

        result = subprocess.run(
            ["python", "tools/test-icons.py"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        print("  test-icons exit code on broken code: %d" % result.returncode)

        if result.returncode == 0:
            print()
            print("  FAIL  the test passed on code that cannot open a window.")
            print("        It is not testing what it claims to test.")
            for line in result.stdout.strip().splitlines()[-6:]:
                print("    %s" % line)
            return 1

        print("  the test caught it:")
        for line in result.stdout.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("FAIL"):
                print("    %s" % stripped[:100])
                break

    finally:
        ICONS.write_bytes(BACKUP.read_bytes())
        restored = build()
        print("  restored the real icon builder (build %s)"
              % ("OK" if restored else "FAILED - check Icons.cs"))

    print()
    print("  OK    the icon test fails when the icon builder is broken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
