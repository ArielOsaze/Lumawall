// Icons.cs - the app's vector icon set.
//
// The geometry is Lucide (lucide, ISC), converted from its SVGs to the
// stroked path strings this file has always used. Nothing here is hand-drawn:
// a set where each icon is invented separately is a set with no shared
// proportions, and the result reads as placeholder art.
//
// Lucide was chosen because it is already the shape this app needs - outline
// style, 24x24 grid, 2px stroke, round caps and joins, no colour of its own -
// so the app keeps control of the tint and every icon matches the others.
//
// The app deliberately does not use an icon font: the previous build drew
// Segoe Fluent glyphs, which fall back to unrelated or blank shapes when a
// user's Windows build ships a different symbol font. Every icon here is a
// stroked Path drawn from explicit geometry, so it renders identically on
// every machine and stays crisp at any DPI.
//
// All icons are authored on a 24x24 grid and scaled by the caller.
//
// Regenerate with: python tools/apply-lucide-icons.py

using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace LumaWall
{
    internal static class Icons
    {
        public const string Dashboard = "dashboard";
        public const string Library = "library";
        public const string Catalog = "catalog";
        public const string Displays = "displays";
        public const string Performance = "performance";
        public const string Search = "search";
        public const string Add = "add";
        public const string Apply = "apply";
        public const string Download = "download";
        public const string Stop = "stop";
        public const string Optimize = "optimize";
        public const string Cpu = "cpu";
        public const string Memory = "memory";
        public const string Wallpaper = "wallpaper";
        public const string Warning = "warning";
        public const string Empty = "empty";
        public const string Check = "check";
        public const string Save = "save";
        public const string Power = "power";
        public const string Image = "image";
        public const string AllDisplays = "all-displays";
        public const string Close = "close";
        public const string Minimize = "minimize";
        public const string Maximize = "maximize";
        public const string Restore = "restore";
        public const string Studio = "studio";
        public const string Palette = "palette";
        public const string Filter = "filter";
        public const string Flip = "flip";
        public const string Hdr = "hdr";
        public const string Frame = "frame";
        public const string Speed = "speed";
        public const string Timer = "timer";
        public const string Reset = "reset";

        private const double Grid = 24d;

        /// <summary>
        /// Builds a stroked vector icon. Stroke keeps the shape legible on both
        /// the dark shell and the crimson primary buttons. Returns FrameworkElement
        /// so call sites can still set alignment and margin.
        /// </summary>
        public static FrameworkElement Build(string name, double size, Brush brush, bool filled = false)
        {
            // Icons are drawn at whole sizes. A fractional size puts every coordinate and the
            // stroke itself on part of a pixel, which is the difference between an icon that
            // reads as drawn and one that reads as smudged.
            size = Math.Round(size);

            var canvas = new Canvas
            {
                Width = size,
                Height = size,
                SnapsToDevicePixels = true,
                UseLayoutRounding = true
            };
            foreach (string data in GeometryFor(name))
            {
                var path = new Path
                {
                    Data = Geometry.Parse(data),
                    Stroke = brush,
                    // Lucide is drawn at 2px on a 24px grid. The stroke is set here rather
                    // than scaled with the icon so a 14px icon keeps a hairline weight
                    // instead of becoming a blob.
                    StrokeThickness = filled ? 0d : 1.9d,
                    StrokeStartLineCap = PenLineCap.Round,
                    StrokeEndLineCap = PenLineCap.Round,
                    StrokeLineJoin = PenLineJoin.Round,
                    Fill = filled ? brush : null,
                    SnapsToDevicePixels = true,
                    UseLayoutRounding = true
                };
                canvas.Children.Add(path);
            }

            // The scale is applied at render time. It cannot be baked into the geometry:
            // Geometry.Parse returns a frozen geometry, and setting Transform on a frozen
            // Freezable throws InvalidOperationException. That fault took the whole window
            // down when it was tried, so the transform stays here.
            double scale = size / Grid;
            canvas.RenderTransform = new ScaleTransform(scale, scale);
            canvas.RenderTransformOrigin = new Point(0, 0);
            return canvas;
        }

        private static IEnumerable<string> GeometryFor(string name)
        {
            switch (name)
            {
                // lucide:layout-grid
                case Dashboard:
                    yield return "M4,3 L9,3 A1,1 0 0 1 10,4 L10,9 A1,1 0 0 1 9,10 L4,10 A1,1 0 0 1 3,9 L3,4 A1,1 0 0 1 4,3 Z";
                    yield return "M15,3 L20,3 A1,1 0 0 1 21,4 L21,9 A1,1 0 0 1 20,10 L15,10 A1,1 0 0 1 14,9 L14,4 A1,1 0 0 1 15,3 Z";
                    yield return "M15,14 L20,14 A1,1 0 0 1 21,15 L21,20 A1,1 0 0 1 20,21 L15,21 A1,1 0 0 1 14,20 L14,15 A1,1 0 0 1 15,14 Z";
                    yield return "M4,14 L9,14 A1,1 0 0 1 10,15 L10,20 A1,1 0 0 1 9,21 L4,21 A1,1 0 0 1 3,20 L3,15 A1,1 0 0 1 4,14 Z";
                    break;

                // lucide:library
                case Library:
                    yield return "m16 6 4 14";
                    yield return "M12 6v14";
                    yield return "M8 8v12";
                    yield return "M4 4v16";
                    break;

                // lucide:compass
                case Catalog:
                    yield return "M2,12 A10,10 0 1 1 22,12 A10,10 0 1 1 2,12 Z";
                    yield return "m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z";
                    break;

                // lucide:monitor
                case Displays:
                    yield return "M4,3 L20,3 A2,2 0 0 1 22,5 L22,15 A2,2 0 0 1 20,17 L4,17 A2,2 0 0 1 2,15 L2,5 A2,2 0 0 1 4,3 Z";
                    yield return "M8,21 L16,21";
                    yield return "M12,17 L12,21";
                    break;

                // lucide:gauge
                case Performance:
                    yield return "m12 14 4-4";
                    yield return "M3.34 19a10 10 0 1 1 17.32 0";
                    break;

                // lucide:search
                case Search:
                    yield return "m21 21-4.34-4.34";
                    yield return "M3,11 A8,8 0 1 1 19,11 A8,8 0 1 1 3,11 Z";
                    break;

                // lucide:plus
                case Add:
                    yield return "M5 12h14";
                    yield return "M12 5v14";
                    break;

                // lucide:play
                case Apply:
                    yield return "M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z";
                    break;

                // lucide:download
                case Download:
                    yield return "M12 15V3";
                    yield return "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4";
                    yield return "m7 10 5 5 5-5";
                    break;

                // lucide:square
                case Stop:
                    yield return "M5,3 L19,3 A2,2 0 0 1 21,5 L21,19 A2,2 0 0 1 19,21 L5,21 A2,2 0 0 1 3,19 L3,5 A2,2 0 0 1 5,3 Z";
                    break;

                // lucide:zap
                case Optimize:
                    yield return "M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z";
                    break;

                // lucide:cpu
                case Cpu:
                    yield return "M12 20v2";
                    yield return "M12 2v2";
                    yield return "M17 20v2";
                    yield return "M17 2v2";
                    yield return "M2 12h2";
                    yield return "M2 17h2";
                    yield return "M2 7h2";
                    yield return "M20 12h2";
                    yield return "M20 17h2";
                    yield return "M20 7h2";
                    yield return "M7 20v2";
                    yield return "M7 2v2";
                    yield return "M6,4 L18,4 A2,2 0 0 1 20,6 L20,18 A2,2 0 0 1 18,20 L6,20 A2,2 0 0 1 4,18 L4,6 A2,2 0 0 1 6,4 Z";
                    yield return "M9,8 L15,8 A1,1 0 0 1 16,9 L16,15 A1,1 0 0 1 15,16 L9,16 A1,1 0 0 1 8,15 L8,9 A1,1 0 0 1 9,8 Z";
                    break;

                // lucide:memory-stick
                case Memory:
                    yield return "M12 12v-2";
                    yield return "M12 18v-2";
                    yield return "M16 12v-2";
                    yield return "M16 18v-2";
                    yield return "M2 11h1.5";
                    yield return "M20 18v-2";
                    yield return "M20.5 11H22";
                    yield return "M4 18v-2";
                    yield return "M8 12v-2";
                    yield return "M8 18v-2";
                    yield return "M4,6 L20,6 A2,2 0 0 1 22,8 L22,14 A2,2 0 0 1 20,16 L4,16 A2,2 0 0 1 2,14 L2,8 A2,2 0 0 1 4,6 Z";
                    break;

                // lucide:images
                case Wallpaper:
                    yield return "m22 11-1.296-1.296a2.4 2.4 0 0 0-3.408 0L11 16";
                    yield return "M4 8a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2";
                    yield return "M12,7 A1,1 0 1 1 14,7 A1,1 0 1 1 12,7 Z";
                    yield return "M10,2 L20,2 A2,2 0 0 1 22,4 L22,14 A2,2 0 0 1 20,16 L10,16 A2,2 0 0 1 8,14 L8,4 A2,2 0 0 1 10,2 Z";
                    break;

                // lucide:triangle-alert
                case Warning:
                    yield return "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3";
                    yield return "M12 9v4";
                    yield return "M12 17h.01";
                    break;

                // lucide:inbox
                case Empty:
                    yield return "M22,12 L16,12 L14,15 L10,15 L8,12 L2,12";
                    yield return "M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z";
                    break;

                // lucide:check
                case Check:
                    yield return "M20 6 9 17l-5-5";
                    break;

                // lucide:save
                case Save:
                    yield return "M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z";
                    yield return "M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7";
                    yield return "M7 3v4a1 1 0 0 0 1 1h7";
                    break;

                // lucide:power
                case Power:
                    yield return "M12 2v10";
                    yield return "M18.4 6.6a9 9 0 1 1-12.77.04";
                    break;

                // lucide:image
                case Image:
                    yield return "M5,3 L19,3 A2,2 0 0 1 21,5 L21,19 A2,2 0 0 1 19,21 L5,21 A2,2 0 0 1 3,19 L3,5 A2,2 0 0 1 5,3 Z";
                    yield return "M7,9 A2,2 0 1 1 11,9 A2,2 0 1 1 7,9 Z";
                    yield return "m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21";
                    break;

                // lucide:monitor-smartphone
                case AllDisplays:
                    yield return "M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8";
                    yield return "M10 19v-3.96 3.15";
                    yield return "M7 19h5";
                    yield return "M18,12 L20,12 A2,2 0 0 1 22,14 L22,20 A2,2 0 0 1 20,22 L18,22 A2,2 0 0 1 16,20 L16,14 A2,2 0 0 1 18,12 Z";
                    break;

                // lucide:x
                case Close:
                    yield return "M18 6 6 18";
                    yield return "m6 6 12 12";
                    break;

                // lucide:minus
                case Minimize:
                    yield return "M5 12h14";
                    break;

                // lucide:square
                case Maximize:
                    yield return "M5,3 L19,3 A2,2 0 0 1 21,5 L21,19 A2,2 0 0 1 19,21 L5,21 A2,2 0 0 1 3,19 L3,5 A2,2 0 0 1 5,3 Z";
                    break;

                // lucide:copy
                case Restore:
                    yield return "M10,8 L20,8 A2,2 0 0 1 22,10 L22,20 A2,2 0 0 1 20,22 L10,22 A2,2 0 0 1 8,20 L8,10 A2,2 0 0 1 10,8 Z";
                    yield return "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2";
                    break;

                // lucide:sliders-horizontal
                case Studio:
                    yield return "M10 5H3";
                    yield return "M12 19H3";
                    yield return "M14 3v4";
                    yield return "M16 17v4";
                    yield return "M21 12h-9";
                    yield return "M21 19h-5";
                    yield return "M21 5h-7";
                    yield return "M8 10v4";
                    yield return "M8 12H3";
                    break;

                // lucide:palette
                case Palette:
                    yield return "M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z";
                    yield return "M13,6.5 A0.5,0.5 0 1 1 14,6.5 A0.5,0.5 0 1 1 13,6.5 Z";
                    yield return "M17,10.5 A0.5,0.5 0 1 1 18,10.5 A0.5,0.5 0 1 1 17,10.5 Z";
                    yield return "M6,12.5 A0.5,0.5 0 1 1 7,12.5 A0.5,0.5 0 1 1 6,12.5 Z";
                    yield return "M8,7.5 A0.5,0.5 0 1 1 9,7.5 A0.5,0.5 0 1 1 8,7.5 Z";
                    break;

                // lucide:funnel
                case Filter:
                    yield return "M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z";
                    break;

                // lucide:flip-horizontal
                case Flip:
                    yield return "M8 3H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h3";
                    yield return "M16 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3";
                    yield return "M12 20v2";
                    yield return "M12 14v2";
                    yield return "M12 8v2";
                    yield return "M12 2v2";
                    break;

                // lucide:sun
                case Hdr:
                    yield return "M8,12 A4,4 0 1 1 16,12 A4,4 0 1 1 8,12 Z";
                    yield return "M12 2v2";
                    yield return "M12 20v2";
                    yield return "m4.93 4.93 1.41 1.41";
                    yield return "m17.66 17.66 1.41 1.41";
                    yield return "M2 12h2";
                    yield return "M20 12h2";
                    yield return "m6.34 17.66-1.41 1.41";
                    yield return "m19.07 4.93-1.41 1.41";
                    break;

                // lucide:crop
                case Frame:
                    yield return "M6 2v14a2 2 0 0 0 2 2h14";
                    yield return "M18 22V8a2 2 0 0 0-2-2H2";
                    break;

                // lucide:timer
                case Speed:
                    yield return "M10,2 L14,2";
                    yield return "M12,14 L15,11";
                    yield return "M4,14 A8,8 0 1 1 20,14 A8,8 0 1 1 4,14 Z";
                    break;

                // lucide:clock
                case Timer:
                    yield return "M2,12 A10,10 0 1 1 22,12 A10,10 0 1 1 2,12 Z";
                    yield return "M12 6v6l4 2";
                    break;

                // lucide:rotate-ccw
                case Reset:
                    yield return "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8";
                    yield return "M3 3v5h5";
                    break;

                default:
                    yield return "M4,12 L20,12";
                    break;
            }
        }
    }
}
