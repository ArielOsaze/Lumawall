"""Build every icon at every size the app uses, and fail on any exception.

Why this exists: `Geometry.Parse` returns a frozen geometry, and an attempt to bake the
scale into it by setting `.Transform` threw `InvalidOperationException` - inside the icon
builder, which runs while the window is being constructed. The window did not appear at
all, and the only trace was a line in the render tool's output. Nothing in the test suite
covered the icon set, so a change that made every icon fatal built and shipped clean.

This walks the real assembly and calls the real `Icons.Build`, so it fails exactly where
the app would.

Run: powershell -File tools/test-icons.ps1
"""

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "LumaWall" / "bin" / "Release" / "LumaWall.exe"


def main():
    if not APP.exists():
        print("  %s is missing - build the app first" % APP)
        return 1

    # A stale binary is the trap this test already fell into once: the build failed, the
    # previous LumaWall.exe was still on disk, and the test loaded it and reported success
    # about code that never compiled. Refuse to test a binary older than its sources.
    newest_source = max(
        (p.stat().st_mtime for p in (ROOT / "LumaWall").glob("*.cs")),
        default=0,
    )
    if APP.stat().st_mtime < newest_source:
        print("  %s is older than the sources it was built from" % APP.name)
        print("  build the app first - testing a stale binary proves nothing")
        return 1

    script = textwrap.dedent(r"""
        Add-Type -AssemblyName PresentationCore, PresentationFramework, WindowsBase
        $assembly = [System.Reflection.Assembly]::LoadFrom("%s")

        $icons = $assembly.GetType("LumaWall.Icons")
        if (-not $icons) { Write-Host "  cannot find LumaWall.Icons"; exit 2 }

        # Every size the app asks for, taken from the call sites rather than invented.
        $sizes = @(10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 26, 28, 32)
        $names = $icons.GetFields([System.Reflection.BindingFlags]::Public -bor `
                                  [System.Reflection.BindingFlags]::Static) |
            Where-Object { $_.FieldType -eq [string] } |
            ForEach-Object { $_.GetValue($null) }

        $build = $icons.GetMethod("Build", [type[]]@([string], [double],
            [System.Windows.Media.Brush], [bool]))
        if (-not $build) { Write-Host "  cannot find Icons.Build"; exit 2 }

        $brush = [System.Windows.Media.Brushes]::White
        $failures = 0
        $built = 0
        $sizesSeen = @{}
        $noArt = @()

        foreach ($name in $names) {
            foreach ($size in $sizes) {
                try {
                    $element = $build.Invoke($null, @($name, [double]$size, $brush, $false))
                    if ($null -eq $element) {
                        Write-Host ("  FAIL  {0} at {1}px returned nothing" -f $name, $size)
                        $failures++
                        continue
                    }
                    $canvas = [System.Windows.Controls.Canvas]$element
                    if ($canvas.Children.Count -eq 0) {
                        # Only report the default fallback, which draws one line and is what
                        # an unknown name gets.
                        if ($noArt -notcontains $name) { $noArt += $name }
                    }
                    $built++
                    $sizesSeen[[int]$size] = $true
                } catch {
                    Write-Host ("  FAIL  {0} at {1}px : {2}" -f $name, $size, $_.Exception.Message)
                    $failures++
                }
            }
        }

        Write-Host ("  icons built : {0}" -f $names.Count)
        Write-Host ("  sizes tried : {0}" -f (($sizesSeen.Keys | Sort-Object) -join ", "))
        Write-Host ("  builds ok   : {0}" -f $built)

        if ($noArt.Count -gt 0) {
            Write-Host ("  FAIL  {0} icon(s) draw nothing: {1}" -f $noArt.Count, ($noArt -join ", "))
            $failures += $noArt.Count
        }

        if ($failures -gt 0) {
            Write-Host ("  {0} failure(s)." -f $failures)
            exit 1
        }
        Write-Host "  OK    every icon builds at every size."
        exit 0
    """ % str(APP).replace("\\", "\\\\"))

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
