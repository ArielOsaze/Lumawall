// TimerPreview.cs - render the desktop timer to a PNG, using the widget's own drawing.
//
// Why this exists
// ---------------
// The timer styles have to be checked, and a screenshot cannot check them: the widget is a
// layered window over the wallpaper, so a screen capture contains the wallpaper as well,
// and a checker that thresholds "bright pixels" then measures the wallpaper. That happened -
// the check reported every style at 93% ink with a full-height clock band, which was the
// wallpaper showing through.
//
// The FIRST version of this file then made a different mistake: it re-implemented the
// layout instead of calling the widget's. The two disagreed - the preview drew ioslarge at
// 329x307 while the widget drew it at 353x167 - so a check based on the preview would have
// been checking a drawing the user never sees.
//
// So this creates the real TimerWindow, gives it the same config the widget gets, and
// captures the bitmap it paints through DrawFrame. What the checker reads is byte-for-byte
// what the widget puts on the desktop.

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;

namespace LumaWall
{
    /// <summary>
    /// Renders every timer style to build/timer-preview/&lt;style&gt;.png.
    ///
    /// Invoked by the app itself: LumaWall.exe --render-timer &lt;output-directory&gt;.
    /// </summary>
    internal static class TimerPreview
    {
        // The styles the Studio page offers, in the order it shows them. Kept in step with
        // DesktopTimer.Style() by tools/check-timer-styles.py, which fails when a style the
        // page offers has no preview.
        private static readonly string[] Styles =
        {
            "minimal", "bold", "glass", "card", "ring", "analog",
            "ioslarge", "ioslight", "iosstack", "iosdate",
        };

        /// <summary>The reading every style is rendered with, so the shots compare.</summary>
        private const string Time = "9:41";
        private const string Date = "Sunday, 27 September";

        /// <summary>The useful half of a reflection exception.</summary>
        private static string Describe(Exception error)
        {
            Exception inner = error.InnerException;
            return inner == null ? error.Message : inner.ToString();
        }

        public static int Render(string outputDirectory)
        {
            try
            {
                Directory.CreateDirectory(outputDirectory);

                // The widget type and its window are private to the timer. Reflection is
                // deliberate: the alternative is a second copy of the drawing code, which is
                // the mistake this file already made once.
                Type timerType = typeof(DesktopTimer);
                Type windowType = timerType.GetNestedType("TimerWindow",
                    BindingFlags.NonPublic | BindingFlags.Public);
                if (windowType == null)
                {
                    Console.Error.WriteLine("  TimerWindow not found inside DesktopTimer");
                    return 1;
                }

                // The sink lives on the window type; it is set once and receives every frame.
                FieldInfo sink = windowType.GetField("PreviewSink",
                    BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static);
                // Draw() is the entry point, not DrawFrame: Draw measures the text, sizes the
                // window and then paints. Calling DrawFrame directly would hand it a bitmap
                // that was never sized for the style.
                MethodInfo drawFrame = windowType.GetMethod("Draw",
                    BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance);
                MethodInfo show = windowType.GetMethod("Show",
                    BindingFlags.Public | BindingFlags.Instance, null, Type.EmptyTypes, null);
                if (sink == null || drawFrame == null)
                {
                    Console.Error.WriteLine("  the preview hooks are missing from TimerWindow");
                    return 1;
                }

                foreach (string style in Styles)
                {
                    object window = Activator.CreateInstance(windowType, true);
                    try
                    {
                        var config = new TimerConfig
                        {
                            Enabled = true,
                            Style = style,
                            Mode = "clock",
                            ShowDate = true,
                            TwelveHour = false,
                            Scale = 150,
                            Position = "middle-center",
                        };

                        // Show it so Width/Height and the handle exist; it is never placed on
                        // the desktop and the app exits before any of it is seen.
                        try { if (show != null) show.Invoke(window, null); }
                        catch (Exception e) { Console.Error.WriteLine("  show: " + Describe(e)); }

                        Bitmap captured = null;
                        Action<Bitmap> capture = delegate(Bitmap b)
                        {
                            captured = new Bitmap(b);
                        };
                        sink.SetValue(null, capture);

                        // Draw once with the reading, once more because the widget skips a
                        // repaint whose content has not changed.
                        var args = new object[] { Time, Date, 0.65, config, false, false };
                        try { drawFrame.Invoke(window, args); }
                        catch (Exception e) { Console.Error.WriteLine("  draw: " + Describe(e)); }
                        try { drawFrame.Invoke(window, args); }
                        catch (Exception e) { Console.Error.WriteLine("  draw2: " + Describe(e)); }

                        sink.SetValue(null, null);

                        if (captured == null)
                        {
                            Console.Error.WriteLine("  {0,-10} drew nothing", style);
                            return 1;
                        }

                        string path = Path.Combine(outputDirectory, style + ".png");
                        captured.Save(path, ImageFormat.Png);
                        Console.WriteLine("  {0,-10} {1}x{2}", style, captured.Width, captured.Height);
                        captured.Dispose();
                    }
                    finally
                    {
                        var dispose = window as IDisposable;
                        if (dispose != null) dispose.Dispose();
                    }
                }
                return 0;
            }
            catch (Exception error)
            {
                Console.Error.WriteLine("  render failed: " + error);
                return 1;
            }
        }
    }
}
