"""Replace LumaWall's hand-drawn icons with Lucide's.

Why: the icon set was drawn by hand, one path per icon, and it showed. The Catalog icon
was a circle with a slash - which reads as "prohibited", not "catalogue" - and the Library
icon was three horizontal lines, the most generic mark there is. A screenshot of the
dashboard was reported as looking like AI-generated placeholder art, which is a fair
description of a set where each icon was invented separately.

Lucide is the right replacement: outline style on the same 24x24 grid the app already
uses, 2px stroke, consistent geometry across every icon, ISC licensed, and no colour of
its own - so the app keeps control of the tint and nothing is "warna-warni".

This writes LumaWall/Icons.cs from build/icons-lucide.json, which is produced by fetching
the real Lucide package rather than by drawing anything. The header comment is kept
because it explains why the app draws paths instead of using an icon font.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "build" / "icons-lucide.json"
TARGET = ROOT / "LumaWall" / "Icons.cs"

# The const names the rest of the app refers to. Kept in the same order as the JSON so a
# diff shows a mapping change rather than a reordering.
CONST_NAMES = {
    "Dashboard": "Dashboard",
    "Library": "Library",
    "Catalog": "Catalog",
    "Displays": "Displays",
    "Performance": "Performance",
    "Search": "Search",
    "Add": "Add",
    "Apply": "Apply",
    "Download": "Download",
    "Stop": "Stop",
    "Optimize": "Optimize",
    "Cpu": "Cpu",
    "Memory": "Memory",
    "Wallpaper": "Wallpaper",
    "Warning": "Warning",
    "Empty": "Empty",
    "Check": "Check",
    "Save": "Save",
    "Power": "Power",
    "Image": "Image",
    "AllDisplays": "AllDisplays",
    "Close": "Close",
    "Minimize": "Minimize",
    "Maximize": "Maximize",
    "Restore": "Restore",
    "Studio": "Studio",
    "Palette": "Palette",
    "Filter": "Filter",
    "Flip": "Flip",
    "Hdr": "Hdr",
    "Frame": "Frame",
    "Speed": "Speed",
    "Timer": "Timer",
    # The reset button's own name. The app already had a `Restore` for the window control,
    # so this one is spelled out rather than overloading that one.
    "RestoreReset": "Reset",
}

# Which icons are solid rather than stroked. All of Lucide's are stroked, so this is empty
# and exists so the writer does not have to assume it.
FILLED = set()


def main():
    if not SOURCE.exists():
        print("  %s is missing" % SOURCE)
        print("  it is produced by fetching the Lucide package; see the delegation notes")
        return 1

    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    icons = data.get("icons", [])
    source = data.get("source", {})

    if not icons:
        print("  no icons in %s" % SOURCE)
        return 1

    lines = []
    lines.append("// Icons.cs - the app's vector icon set.")
    lines.append("//")
    lines.append("// The geometry is Lucide (%s, %s), converted from its SVGs to the"
                 % (source.get("set", "lucide"), source.get("licence", "ISC")))
    lines.append("// stroked path strings this file has always used. Nothing here is hand-drawn:")
    lines.append("// a set where each icon is invented separately is a set with no shared")
    lines.append("// proportions, and the result reads as placeholder art.")
    lines.append("//")
    lines.append("// Lucide was chosen because it is already the shape this app needs - outline")
    lines.append("// style, 24x24 grid, 2px stroke, round caps and joins, no colour of its own -")
    lines.append("// so the app keeps control of the tint and every icon matches the others.")
    lines.append("//")
    lines.append("// The app deliberately does not use an icon font: the previous build drew")
    lines.append("// Segoe Fluent glyphs, which fall back to unrelated or blank shapes when a")
    lines.append("// user's Windows build ships a different symbol font. Every icon here is a")
    lines.append("// stroked Path drawn from explicit geometry, so it renders identically on")
    lines.append("// every machine and stays crisp at any DPI.")
    lines.append("//")
    lines.append("// All icons are authored on a 24x24 grid and scaled by the caller.")
    lines.append("//")
    lines.append("// Regenerate with: python tools/apply-lucide-icons.py")
    lines.append("")
    lines.append("using System;")
    lines.append("using System.Collections.Generic;")
    lines.append("using System.Windows;")
    lines.append("using System.Windows.Controls;")
    lines.append("using System.Windows.Media;")
    lines.append("using System.Windows.Shapes;")
    lines.append("")
    lines.append("namespace LumaWall")
    lines.append("{")
    lines.append("    internal static class Icons")
    lines.append("    {")

    for icon in icons:
        app_name = icon["appName"]
        const = CONST_NAMES.get(app_name)
        if not const:
            print("  no const name for %s" % app_name)
            return 1
        lines.append('        public const string %s = "%s";' % (const, _kebab(const)))

    lines.append("")
    lines.append("        private const double Grid = 24d;")
    lines.append("")
    lines.append("        /// <summary>")
    lines.append("        /// Builds a stroked vector icon. Stroke keeps the shape legible on both")
    lines.append("        /// the dark shell and the crimson primary buttons. Returns FrameworkElement")
    lines.append("        /// so call sites can still set alignment and margin.")
    lines.append("        /// </summary>")
    lines.append("        public static FrameworkElement Build(string name, double size, Brush brush, bool filled = false)")
    lines.append("        {")
    lines.append("            // Icons are drawn at whole sizes. A fractional size puts every coordinate and the")
    lines.append("            // stroke itself on part of a pixel, which is the difference between an icon that")
    lines.append("            // reads as drawn and one that reads as smudged.")
    lines.append("            size = Math.Round(size);")
    lines.append("")
    lines.append("            var canvas = new Canvas")
    lines.append("            {")
    lines.append("                Width = size,")
    lines.append("                Height = size,")
    lines.append("                SnapsToDevicePixels = true,")
    lines.append("                UseLayoutRounding = true")
    lines.append("            };")
    lines.append("            foreach (string data in GeometryFor(name))")
    lines.append("            {")
    lines.append("                var path = new Path")
    lines.append("                {")
    lines.append("                    Data = Geometry.Parse(data),")
    lines.append("                    Stroke = brush,")
    lines.append("                    // Lucide is drawn at 2px on a 24px grid. The stroke is set here rather")
    lines.append("                    // than scaled with the icon so a 14px icon keeps a hairline weight")
    lines.append("                    // instead of becoming a blob.")
    lines.append("                    StrokeThickness = filled ? 0d : 1.9d,")
    lines.append("                    StrokeStartLineCap = PenLineCap.Round,")
    lines.append("                    StrokeEndLineCap = PenLineCap.Round,")
    lines.append("                    StrokeLineJoin = PenLineJoin.Round,")
    lines.append("                    Fill = filled ? brush : null,")
    lines.append("                    SnapsToDevicePixels = true,")
    lines.append("                    UseLayoutRounding = true")
    lines.append("                };")
    lines.append("                canvas.Children.Add(path);")
    lines.append("            }")
    lines.append("")
    lines.append("            // The scale is applied at render time. It cannot be baked into the geometry:")
    lines.append("            // Geometry.Parse returns a frozen geometry, and setting Transform on a frozen")
    lines.append("            // Freezable throws InvalidOperationException. That fault took the whole window")
    lines.append("            // down when it was tried, so the transform stays here.")
    lines.append("            double scale = size / Grid;")
    lines.append("            canvas.RenderTransform = new ScaleTransform(scale, scale);")
    lines.append("            canvas.RenderTransformOrigin = new Point(0, 0);")
    lines.append("            return canvas;")
    lines.append("        }")
    lines.append("")
    lines.append("        private static IEnumerable<string> GeometryFor(string name)")
    lines.append("        {")
    lines.append("            switch (name)")
    lines.append("            {")

    for icon in icons:
        app_name = icon["appName"]
        const = CONST_NAMES[app_name]
        lucide = icon.get("lucideName", "")
        lines.append("                // lucide:%s" % lucide)
        lines.append("                case %s:" % const)
        for path in icon.get("paths", []):
            lines.append('                    yield return "%s";' % path.replace("\\", "\\\\").replace('"', '\\"'))
        lines.append("                    break;")
        lines.append("")

    lines.append("                default:")
    lines.append('                    yield return "M4,12 L20,12";')
    lines.append("                    break;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")

    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  wrote %s" % TARGET)
    print("  %d icons, %d paths" % (len(icons), sum(len(i.get("paths", [])) for i in icons)))
    return 0


def _kebab(name):
    """The string the app passes to Icons.Build - lower case, hyphenated."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


if __name__ == "__main__":
    sys.exit(main())
