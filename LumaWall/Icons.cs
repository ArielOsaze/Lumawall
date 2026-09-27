using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace LumaWall
{
    /// <summary>
    /// Hand-built vector icon set for the LumaWall shell.
    ///
    /// The app deliberately does not use an icon font: the previous build drew
    /// Segoe Fluent glyphs, which fall back to unrelated or blank shapes when a
    /// user's Windows build ships a different symbol font, and that reads as
    /// "cheap placeholder" art. Every icon here is a stroked Path drawn from
    /// explicit geometry, so it renders identically on every machine and stays
    /// crisp at any DPI.
    ///
    /// All icons are authored on a 24x24 grid and scaled by the caller.
    /// </summary>
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
        public const string Studio = "studio";
        public const string Palette = "palette";
        public const string Filter = "filter";
        public const string Flip = "flip";
        public const string Hdr = "hdr";
        public const string Frame = "frame";
        public const string Speed = "speed";
        public const string Timer = "timer";
        public const string Close = "close";
        public const string Minimize = "minimize";
        public const string Maximize = "maximize";
        public const string Restore = "restore";

        private const double Grid = 24d;

        /// <summary>
        /// Builds a stroked vector icon. Stroke keeps the shape legible on both
        /// the dark shell and the crimson primary buttons. Returns FrameworkElement
        /// so call sites can still set alignment and margin.
        /// </summary>
        public static FrameworkElement Build(string name, double size, Brush brush, bool filled = false)
        {
            var canvas = new Canvas
            {
                Width = size,
                Height = size,
                SnapsToDevicePixels = true
            };
            foreach (string data in GeometryFor(name))
            {
                var path = new Path
                {
                    Data = Geometry.Parse(data),
                    Stroke = brush,
                    StrokeThickness = filled ? 0d : 1.7d,
                    StrokeStartLineCap = PenLineCap.Round,
                    StrokeEndLineCap = PenLineCap.Round,
                    StrokeLineJoin = PenLineJoin.Round,
                    Fill = filled ? brush : null,
                    SnapsToDevicePixels = true
                };
                canvas.Children.Add(path);
            }
            double scale = size / Grid;
            canvas.RenderTransform = new ScaleTransform(scale, scale);
            canvas.RenderTransformOrigin = new Point(0, 0);
            canvas.Width = size;
            canvas.Height = size;
            return canvas;
        }

        private static IEnumerable<string> GeometryFor(string name)
        {
            switch (name)
            {
                // A 2x2 tile grid: reads as an overview/dashboard surface.
                case Dashboard:
                    yield return "M3.5,3.5 L10.5,3.5 L10.5,10.5 L3.5,10.5 Z";
                    yield return "M13.5,3.5 L20.5,3.5 L20.5,10.5 L13.5,10.5 Z";
                    yield return "M3.5,13.5 L10.5,13.5 L10.5,20.5 L3.5,20.5 Z";
                    yield return "M13.5,13.5 L20.5,13.5 L20.5,20.5 L13.5,20.5 Z";
                    break;

                // Stacked media shelves: the wallpaper collection.
                case Library:
                    yield return "M4,6.5 L20,6.5";
                    yield return "M4,12 L20,12";
                    yield return "M4,17.5 L20,17.5";
                    yield return "M6.5,4 L6.5,9";
                    yield return "M17.5,4 L17.5,9";
                    yield return "M6.5,15 L6.5,20";
                    yield return "M17.5,15 L17.5,20";
                    break;

                // Compass: browse/discover the catalog.
                case Catalog:
                    yield return "M12,3 A9,9 0 1 1 11.99,3 Z";
                    yield return "M15.6,8.4 L13.2,13.2 L8.4,15.6 L10.8,10.8 Z";
                    break;

                // Monitor with a stand: display assignment.
                case Displays:
                    yield return "M3,5 L21,5 L21,16 L3,16 Z";
                    yield return "M9,20 L15,20";
                    yield return "M12,16 L12,20";
                    break;

                // Gauge needle: performance tuning.
                case Performance:
                    yield return "M4,17 A8,8 0 0 1 20,17";
                    yield return "M12,17 L16.2,11.6";
                    yield return "M5.2,14.4 L6.8,15";
                    yield return "M18.8,14.4 L17.2,15";
                    break;

                case Search:
                    yield return "M10.5,4 A6.5,6.5 0 1 1 10.49,4 Z";
                    yield return "M15.4,15.4 L20,20";
                    break;

                case Add:
                    yield return "M12,5 L12,19";
                    yield return "M5,12 L19,12";
                    break;

                // Play triangle: apply a wallpaper.
                case Apply:
                    yield return "M8,5.5 L18.5,12 L8,18.5 Z";
                    break;

                // Tray with a down arrow: catalog download.
                case Download:
                    yield return "M12,4 L12,14";
                    yield return "M7.5,10 L12,14.5 L16.5,10";
                    yield return "M4.5,18.5 L19.5,18.5";
                    break;

                case Stop:
                    yield return "M6.5,6.5 L17.5,6.5 L17.5,17.5 L6.5,17.5 Z";
                    break;

                // Spark: FPS optimization.
                case Optimize:
                    yield return "M13,3 L6.5,13.5 L11.5,13.5 L10.5,21 L17.5,10.5 L12.5,10.5 Z";
                    break;

                // Chip with pins: processor telemetry.
                case Cpu:
                    yield return "M7,7 L17,7 L17,17 L7,17 Z";
                    yield return "M10.5,10.5 L13.5,10.5 L13.5,13.5 L10.5,13.5 Z";
                    yield return "M10,3.5 L10,7";
                    yield return "M14,3.5 L14,7";
                    yield return "M10,17 L10,20.5";
                    yield return "M14,17 L14,20.5";
                    yield return "M3.5,10 L7,10";
                    yield return "M3.5,14 L7,14";
                    yield return "M17,10 L20.5,10";
                    yield return "M17,14 L20.5,14";
                    break;

                // Memory sticks: RAM telemetry.
                case Memory:
                    yield return "M3,7 L21,7 L21,15 L3,15 Z";
                    yield return "M7,15 L7,18";
                    yield return "M12,15 L12,18";
                    yield return "M17,15 L17,18";
                    yield return "M7.5,10 L7.5,12";
                    yield return "M12,10 L12,12";
                    yield return "M16.5,10 L16.5,12";
                    break;

                // Framed picture: wallpaper count.
                case Wallpaper:
                    yield return "M3.5,4.5 L20.5,4.5 L20.5,19.5 L3.5,19.5 Z";
                    yield return "M6.5,16.5 L10.5,11 L13.5,14.5 L16,11.5 L18.5,16.5 Z";
                    yield return "M15.2,7.2 A1.4,1.4 0 1 1 15.19,7.2 Z";
                    break;

                case Image:
                    yield return "M3.5,5 L20.5,5 L20.5,19 L3.5,19 Z";
                    yield return "M7,15.5 L10.5,11.5 L13,14 L15.5,11 L17.5,14";
                    break;

                // Triangle with bang: age gate / cautions.
                case Warning:
                    yield return "M12,4.5 L21,19.5 L3,19.5 Z";
                    yield return "M12,10 L12,14.5";
                    yield return "M12,17 L12,17.2";
                    break;

                // Empty tray: empty-state art.
                case Empty:
                    yield return "M3.5,13 L8.5,13 L10,16 L14,16 L15.5,13 L20.5,13";
                    yield return "M6,5.5 L18,5.5 L20.5,13 L20.5,19 L3.5,19 L3.5,13 Z";
                    break;

                case Check:
                    yield return "M5,12.5 L10,17.5 L19,7";
                    break;

                // Floppy: save profile.
                case Save:
                    yield return "M4.5,4.5 L16,4.5 L19.5,8 L19.5,19.5 L4.5,19.5 Z";
                    yield return "M8,4.5 L8,10 L15,10 L15,4.5";
                    yield return "M8,14 L16,14 L16,19.5 L8,19.5 Z";
                    break;

                // Power ring: startup / engine state.
                case Power:
                    yield return "M12,4.5 L12,11.5";
                    yield return "M7.6,7.2 A6.8,6.8 0 1 0 16.4,7.2";
                    break;

                // Four monitors in a 2x2 arrangement: apply to all.
                case AllDisplays:
                    yield return "M3,4 L10,4 L10,10 L3,10 Z";
                    yield return "M14,4 L21,4 L21,10 L14,10 Z";
                    yield return "M3,13 L10,13 L10,19 L3,19 Z";
                    yield return "M14,13 L21,13 L21,19 L14,19 Z";
                    break;

                // Three sliders with the knobs at different positions: the page where
                // a display's look is tuned. Deliberately not the monitor outline that
                // the Displays page uses - two rail entries with the same icon read as
                // a mistake, and at 19px a user cannot tell them apart at a glance.
                case Studio:
                    yield return "M4,7 L20,7";
                    yield return "M4,12 L20,12";
                    yield return "M4,17 L20,17";
                    yield return "M9.5,4.6 L9.5,9.4";
                    yield return "M15.5,9.6 L15.5,14.4";
                    yield return "M8,14.6 L8,19.4";
                    break;

                // Painter's palette with a thumb hole: colour grading.
                case Palette:
                    yield return "M12,3.5 A8.5,8.5 0 1 0 12,20.5 A2.2,2.2 0 0 0 12,16 A1.6,1.6 0 0 1 12,12.8 A8.5,8.5 0 0 0 12,3.5 Z";
                    yield return "M8.2,7.8 L8.2,7.9";
                    yield return "M15.8,7.8 L15.8,7.9";
                    yield return "M6.6,13 L6.7,13";
                    break;

                // Three overlapping circles, the classic filter mark.
                case Filter:
                    yield return "M9.5,6.5 A4.6,4.6 0 1 1 9.49,6.5 Z";
                    yield return "M14.5,6.5 A4.6,4.6 0 1 1 14.49,6.5 Z";
                    yield return "M12,11 A4.6,4.6 0 1 1 11.99,11 Z";
                    break;

                // A shape and its reflection about a dashed axis.
                case Flip:
                    yield return "M12,3 L12,21";
                    yield return "M9.5,7 L4,12 L9.5,17 Z";
                    yield return "M14.5,7 L20,12 L14.5,17 Z";
                    break;

                // A sun on the horizon: the HDR range.
                case Hdr:
                    yield return "M12,7.5 A4,4 0 1 1 11.99,7.5 Z";
                    yield return "M12,2 L12,4.2";
                    yield return "M12,10.8 L12,13";
                    yield return "M4.5,7.5 L6.7,7.5";
                    yield return "M17.3,7.5 L19.5,7.5";
                    yield return "M3,16.5 L21,16.5";
                    yield return "M3,20 L21,20";
                    break;

                // Crop marks around a frame: how the image sits in the screen.
                case Frame:
                    yield return "M3.5,8 L3.5,3.5 L8,3.5";
                    yield return "M16,3.5 L20.5,3.5 L20.5,8";
                    yield return "M20.5,16 L20.5,20.5 L16,20.5";
                    yield return "M8,20.5 L3.5,20.5 L3.5,16";
                    break;

                // A speedometer needle over an arc: playback rate.
                case Speed:
                    yield return "M3.5,17.5 A8.5,8.5 0 0 1 20.5,17.5";
                    yield return "M12,17.5 L16.6,10.8";
                    yield return "M12,3 L12,5";
                    yield return "M4.9,6.9 L6.3,8.3";
                    yield return "M19.1,6.9 L17.7,8.3";
                    break;

                // Clock face with hands: the desktop timer.
                case Timer:
                    yield return "M12,4 A8.5,8.5 0 1 1 11.99,4 Z";
                    yield return "M12,7.5 L12,12 L15.5,14";
                    break;

                case Close:
                    yield return "M6.5,6.5 L17.5,17.5";
                    yield return "M17.5,6.5 L6.5,17.5";
                    break;

                // Window controls. These must be visually distinct at 11px:
                // minimize is a single bar, maximize a bare box, restore a box
                // behind a box. They previously all fell through to `default`
                // (a single bar), so minimize and maximize rendered identically.
                case Minimize:
                    yield return "M5,12 L19,12";
                    break;

                case Maximize:
                    yield return "M5.5,5.5 L18.5,5.5 L18.5,18.5 L5.5,18.5 Z";
                    break;

                case Restore:
                    // Back window peeking out top-right, front window in front.
                    yield return "M8.5,8.5 L8.5,5.5 L18.5,5.5 L18.5,15.5 L15.5,15.5";
                    yield return "M5.5,8.5 L15.5,8.5 L15.5,18.5 L5.5,18.5 Z";
                    break;

                default:
                    yield return "M4,12 L20,12";
                    break;
            }
        }
    }
}
