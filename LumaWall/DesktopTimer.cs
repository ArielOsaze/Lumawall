// DesktopTimer.cs - the desktop widget: a countdown, a clock, or a stopwatch.
//
// Why a separate top-level window rather than something drawn into the wallpaper page:
//
// The wallpaper window is a child of the desktop (WorkerW). Anything drawn inside it is
// BEHIND every application, so a timer there would be invisible whenever the user has a
// window open - which is most of the time, and exactly when a timer is useful. This is a
// real top-level window instead, so it floats above the desktop like a widget.
//
// It is deliberately not a normal window: no taskbar button, no activation, and
// click-through, so it cannot steal focus from a game or block a click on the desktop.
// A timer that interrupts what the user is doing would be worse than no timer.
//
// ── the look ─────────────────────────────────────────────────────────────────────────
//
// The first version drew a filled rounded rectangle with a hairline border in the accent
// colour. On a wallpaper it read as a system dialog that had lost its window: an opaque
// slab covering the artwork, with a coloured edge that fought whatever was behind it. The
// complaint was "widget timer ini yg kayak jelek bgt" and it was fair.
//
// macOS and iOS widgets do the opposite. They carry no background at all - or a barely
// there frosted wash - and the text is held legible by a soft shadow rather than by a box.
// That is what this draws now:
//
//   minimal   the time alone, with a soft shadow. No fill, no border.
//   glass     the same, over a faint translucent wash. Reads on a busy wallpaper.
//   card      a macOS-widget style rounded panel: translucent, no border, content inset.
//   ring      an iOS timer: a progress arc that empties as the countdown runs.
//
// Transparency here is per-pixel, not a colour key. A layered window painted through
// UpdateLayeredWindow takes a 32bpp ARGB bitmap, so the text can be fully opaque while the
// space around it is fully transparent, and the antialiased edges of the glyphs blend into
// the wallpaper instead of into a mask colour. Colour-key transparency cannot do that: it
// leaves a halo of the key colour around every antialiased edge.

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace LumaWall
{
    /// <summary>
    /// The timer readout: a countdown, a clock, or a stopwatch, drawn on a small layered
    /// window over the desktop.
    ///
    /// Style, size and position come from the config because the right answer depends on
    /// the wallpaper behind it - a bright wallpaper needs a different treatment from a dark
    /// one, and the empty corner is different on every desktop.
    /// </summary>
    internal sealed class DesktopTimer : IDisposable
    {
        private readonly TimerWindow window;
        private readonly System.Windows.Forms.Timer tick;
        private readonly Func<TimerConfig> config;
        private readonly Func<IntPtr> wallpaperHandle;
        private DateTime anchor = DateTime.UtcNow;
        private bool disposed;

        // The countdown's remaining time is derived from a start instant rather than
        // decremented, so a tick that arrives late - after a game hitched, or after the
        // machine slept - cannot make the timer drift slow.
        private TimeSpan remaining;
        private bool running;

        public DesktopTimer(Func<TimerConfig> configSource)
            : this(configSource, null)
        {
        }

        /// <summary>
        /// Creates the timer.
        ///
        /// wallpaperHandleSource reports a live wallpaper window; the widget is placed just
        /// above the desktop that owns it, so it sits at the wallpaper's level rather than
        /// floating over the user's applications. It may be null, in which case the widget
        /// still anchors to the desktop itself.
        /// </summary>
        public DesktopTimer(Func<TimerConfig> configSource, Func<IntPtr> wallpaperHandleSource)
        {
            config = configSource;
            wallpaperHandle = wallpaperHandleSource;
            window = new TimerWindow();
            // 200 ms: fast enough that a seconds display never appears to skip, slow enough
            // that the redraw is invisible in the process list.
            tick = new System.Windows.Forms.Timer();
            tick.Interval = 200;
            tick.Tick += delegate { Render(); };
        }

        public void Start()
        {
            TimerConfig current = config();
            if (current == null || !current.Enabled) { Stop(); return; }
            Reset();
            window.Apply(current);

            // Show, and always start the tick.
            //
            // This used to be Show() only, with Refresh() doing "if (!window.Visible)
            // Show()". That reads correctly and is wrong: Form.Visible reports true for a
            // window that was created and never shown - it exists, so it is "visible" - and
            // the window then sat at 0,0 with a 0x0 client area, painted once, and never
            // ticked again because tick.Start() was inside the same skipped branch. The
            // result was the reported "bug timer ada ga muncul": switched on, no widget.
            window.Show();
            tick.Start();

            // Put it at the wallpaper's level BEFORE the first paint, so it never appears
            // over an application even for one frame.
            ReassertDesktopLevel();
            Render();
        }

        /// <summary>
        /// Keeps the widget at the desktop's level.
        ///
        /// Called on every start and refresh because the z-order is not permanent: any
        /// window that activates can be inserted above, and Explorer recreates the desktop
        /// host when it restarts. Re-asserting costs one SetWindowPos and is what keeps the
        /// widget from creeping up the z-order until it covers an application - which is
        /// the bug this exists to prevent.
        /// </summary>
        private void ReassertDesktopLevel()
        {
            try
            {
                IntPtr anchor = wallpaperHandle == null ? IntPtr.Zero : wallpaperHandle();
                NativeDesktop.PlaceAtDesktopLevel(window.Handle, anchor);
            }
            catch { }
        }

        public void Stop()
        {
            tick.Stop();
            window.Hide();
        }

        /// <summary>Re-reads the config: used when the user changes a setting.</summary>
        public void Refresh()
        {
            TimerConfig current = config();
            if (current == null || !current.Enabled) { Stop(); return; }
            window.Apply(current);

            // Show and start the tick unconditionally, for the reason given in Start():
            // "if (!window.Visible)" is not a reliable test of whether the widget is on
            // screen, and gating the tick on it left the widget frozen and invisible.
            window.Show();
            tick.Start();

            // A refresh follows a settings change, and the widget may have been pushed up
            // the z-order since it was created. Re-assert before painting the new look.
            ReassertDesktopLevel();
            Render();
        }

        /// <summary>Restarts a countdown from the top, or resets a stopwatch to zero.</summary>
        public void Reset()
        {
            anchor = DateTime.UtcNow;
            TimerConfig current = config();
            int seconds = current == null ? 300 : Math.Max(1, current.Seconds);
            remaining = TimeSpan.FromSeconds(seconds);
            running = true;
        }

        public void Pause()
        {
            if (running)
            {
                running = false;
                remaining = Remaining();
            }
            else
            {
                running = true;
                anchor = DateTime.UtcNow;
            }
        }

        private TimeSpan Remaining()
        {
            TimerConfig current = config();
            if (current == null) return TimeSpan.Zero;
            if (current.Mode == "stopwatch")
            {
                if (!running) return remaining;
                return DateTime.UtcNow - anchor;
            }
            if (current.Mode == "clock") return DateTime.Now.TimeOfDay;
            if (!running) return remaining;
            TimeSpan left = TimeSpan.FromSeconds(Math.Max(1, current.Seconds)) - (DateTime.UtcNow - anchor);
            return left < TimeSpan.Zero ? TimeSpan.Zero : left;
        }

        /// <summary>Paints the window with what the timer currently reads.</summary>
        private void Render()
        {
            if (disposed) return;
            TimerConfig current = config();
            if (current == null || !current.Enabled) { Stop(); return; }

            TimeSpan value = Remaining();

            bool finished = current.Mode == "countdown" && value <= TimeSpan.Zero;
            // A countdown that reaches zero blinks, because a silent 00:00 on a desktop the
            // user is not looking at is not a notification.
            bool dim = finished && current.BlinkAtEnd && ((DateTime.UtcNow.Millisecond / 500) % 2 == 0);

            window.Draw(Format(value, current), Subtitle(current), Progress(value, current),
                        current, finished, dim);
        }

        /// <summary>
        /// The small line under the time: the date for a clock, the mode for the others.
        ///
        /// A macOS widget is a big reading over a small label, and the label is what makes
        /// the big number mean something. "14:32" alone is a number; "14:32 / Rabu, 27
        /// September" is a clock.
        /// </summary>
        private static string Subtitle(TimerConfig current)
        {
            if (current.Mode == "clock")
            {
                if (!current.ShowDate) return "";
                CultureInfo culture = CultureInfo.CurrentUICulture;
                // "Rabu, 27 September" / "Wednesday, 27 September" - long day and month,
                // which is the macOS lock screen form.
                return DateTime.Now.ToString("dddd, d MMMM", culture);
            }
            return "";
        }

        /// <summary>How full the ring is: 1 at the start of a countdown, 0 at the end.</summary>
        private static double Progress(TimeSpan value, TimerConfig current)
        {
            if (current.Mode == "stopwatch") return 1.0;
            if (current.Mode == "clock")
            {
                // The seconds hand of a ring clock, so the arc moves once a minute.
                return 1.0 - (DateTime.Now.TimeOfDay.TotalSeconds % 60) / 60.0;
            }
            double total = Math.Max(1, current.Seconds);
            double left = Math.Max(0, value.TotalSeconds);
            return Math.Max(0, Math.Min(1, left / total));
        }

        private static string Format(TimeSpan value, TimerConfig current)
        {
            if (current.Mode == "clock")
            {
                DateTime now = DateTime.Now;
                if (current.TwelveHour)
                {
                    // No leading zero, the way macOS and iOS show a clock: "9:41", not
                    // "09:41". The leading zero makes a desktop clock look like a log line.
                    string format = current.ShowSeconds ? "h:mm:ss" : "h:mm";
                    return now.ToString(format, CultureInfo.InvariantCulture);
                }
                return current.ShowSeconds
                    ? now.ToString("HH:mm:ss", CultureInfo.InvariantCulture)
                    : now.ToString("HH:mm", CultureInfo.InvariantCulture);
            }

            if (value < TimeSpan.Zero) value = TimeSpan.Zero;
            int hours = (int)value.TotalHours;
            if (hours > 0)
                return string.Format(CultureInfo.InvariantCulture, "{0}:{1:00}:{2:00}", hours, value.Minutes, value.Seconds);
            return current.ShowSeconds
                ? string.Format(CultureInfo.InvariantCulture, "{0:00}:{1:00}", value.Minutes, value.Seconds)
                : string.Format(CultureInfo.InvariantCulture, "{0:00}", Math.Ceiling(value.TotalMinutes));
        }

        public void Dispose()
        {
            disposed = true;
            tick.Stop();
            tick.Dispose();
            window.Dispose();
        }

        /// <summary>
        /// The window itself.
        ///
        /// A layered window rather than a WPF one, because the desktop timer must not appear
        /// in Alt-Tab, must not take focus, and must let clicks through to whatever is
        /// underneath. It is painted through UpdateLayeredWindow so it can be genuinely
        /// transparent between the glyphs.
        /// </summary>
        private sealed class TimerWindow : Form
        {
            private const int WS_EX_LAYERED = 0x00080000;
            private const int WS_EX_TRANSPARENT = 0x00000020;
            private const int WS_EX_TOOLWINDOW = 0x00000080;
            private const int WS_EX_NOACTIVATE = 0x08000000;
            private const int SW_SHOWNOACTIVATE = 4;
            private const int ULW_ALPHA = 0x00000002;
            private const byte AC_SRC_OVER = 0x00;
            private const byte AC_SRC_ALPHA = 0x01;

            [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int command);
            [DllImport("user32.dll")] private static extern bool UpdateLayeredWindow(
                IntPtr hwnd, IntPtr hdcDst, ref POINT pptDst, ref SIZE psize,
                IntPtr hdcSrc, ref POINT pptSrc, int crKey, ref BLENDFUNCTION pblend, int dwFlags);
            [DllImport("user32.dll")] private static extern IntPtr GetDC(IntPtr hWnd);
            [DllImport("user32.dll")] private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);
            [DllImport("gdi32.dll")] private static extern IntPtr CreateCompatibleDC(IntPtr hDC);
            [DllImport("gdi32.dll")] private static extern bool DeleteDC(IntPtr hDC);
            [DllImport("gdi32.dll")] private static extern IntPtr SelectObject(IntPtr hDC, IntPtr hObject);
            [DllImport("gdi32.dll")] private static extern bool DeleteObject(IntPtr hObject);

            [StructLayout(LayoutKind.Sequential)] private struct POINT { public int X, Y; }
            [StructLayout(LayoutKind.Sequential)] private struct SIZE { public int cx, cy; }
            [StructLayout(LayoutKind.Sequential, Pack = 1)]
            private struct BLENDFUNCTION
            {
                public byte BlendOp, BlendFlags, SourceConstantAlpha, AlphaFormat;
            }

            private TimerConfig current = new TimerConfig();
            private string lastText = "", lastSubtitle = "";
            private bool lastFinished, lastDim;
            private double lastProgress = -1;
            private string lastStyle = "";
            private float lastScale = -1;
            private int lastWidth, lastHeight;

            public TimerWindow()
            {
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                // NOT topmost. A topmost window floats above every application, so the
                // clock sat on top of whatever the user was reading or playing. The window
                // is placed at the desktop's level instead - above the wallpaper, below
                // every app - by NativeDesktop.PlaceAtDesktopLevel().
                TopMost = false;
                // No BackColor and no Opacity: the window is painted entirely through
                // UpdateLayeredWindow, and setting either would make Windows composite the
                // form itself underneath the bitmap we hand it.
                DoubleBuffered = true;
            }

            protected override bool ShowWithoutActivation { get { return true; } }

            protected override CreateParams CreateParams
            {
                get
                {
                    CreateParams parameters = base.CreateParams;
                    parameters.ExStyle |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE;
                    return parameters;
                }
            }

            protected override void OnShown(EventArgs e)
            {
                base.OnShown(e);
                // Shown without activation: a wallpaper widget that stole focus from a game
                // would be a worse bug than not appearing at all.
                ShowWindow(Handle, SW_SHOWNOACTIVATE);
            }

            // The window is painted through UpdateLayeredWindow, so the normal paint path is
            // suppressed entirely. Without this, Windows paints the form's own background
            // first and the widget gets a black rectangle behind it.
            protected override void OnPaintBackground(PaintEventArgs e) { }
            protected override void OnPaint(PaintEventArgs e) { }

            public void Apply(TimerConfig value)
            {
                current = value ?? new TimerConfig();
            }

            public void Draw(string text, string subtitle, double progress,
                             TimerConfig config, bool finished, bool dim)
            {
                float scale = Math.Max(50, Math.Min(250, config.Scale)) / 100f;
                string style = Style(config);

                // Skip a repaint when nothing visible changed. At 5 Hz a clock would
                // otherwise redraw 5 times a second for no reason, and each redraw rebuilds
                // a bitmap and calls UpdateLayeredWindow.
                //
                // Style and scale are part of the comparison, not just the text. Without
                // them, changing the style alone was skipped: the widget kept the old look
                // until the clock happened to tick to a new second. It healed itself within
                // a second, which is exactly why it went unnoticed.
                bool same = text == lastText && subtitle == lastSubtitle
                            && finished == lastFinished && dim == lastDim
                            && style == lastStyle && Math.Abs(scale - lastScale) < 0.001
                            && Math.Abs(progress - lastProgress) < 0.002;
                if (same) return;
                lastText = text; lastSubtitle = subtitle;
                lastFinished = finished; lastDim = dim; lastProgress = progress;
                lastStyle = style; lastScale = scale;

                using (var probe = CreateGraphics())
                {
                    // The size for this style, before anything is measured.
                    //
                    // The per-style sizes used to be applied AFTER the text was measured, so
                    // every style was measured at the shared 30px and every widget came out
                    // 181px wide - bold, ioslarge and ioslight were all the same box with the
                    // same window. The clock inside them was drawn at the right size and then
                    // clipped, which is why the iOS styles looked wrong rather than empty.
                    float timeSize, labelSize;
                    StyleSizes(style, scale, out timeSize, out labelSize);

                    SizeF timeSize2, labelSize2;
                    using (var timeFont = TimeFont(timeSize, style))
                    using (var labelFont = LabelFont(labelSize))
                    {
                        timeSize2 = probe.MeasureString(text, timeFont, int.MaxValue, StringFormat.GenericTypographic);
                        labelSize2 = string.IsNullOrEmpty(subtitle)
                            ? SizeF.Empty
                            : probe.MeasureString(subtitle, labelFont, int.MaxValue, StringFormat.GenericTypographic);
                    }

                    // Both round styles need a square face.
                    //
                    // The ring is an ellipse the moment the window is not square, and the
                    // window is sized from the measured text - so "05:00" produced a wide,
                    // flat oval. The dial has no text at all and needs a square for the same
                    // reason. Measured from the scale alone in both cases.
                    bool round = style == "ring" || style == "analog";
                    int ringPad = style == "ring" ? (int)(26 * scale) : 0;
                    int inset = style == "card" ? (int)(26 * scale) : 0;

                    // The iOS lock screen clock is LARGE - that is the whole look. At the
                    // shared 30px it read as a small digital clock rather than as the lock
                    // screen. ioslarge is the size of the real thing; ioslight is the same
                    // face, a step smaller; iosstack is the stacked time-and-date widget.
                    // The size for the style is already applied in StyleSizes - the old
                    // multipliers that lived here (x2.1 for ioslarge, x1.5 for iosstack) are
                    // gone. They were written when the iOS styles shared the 30px base and
                    // needed to be scaled up from it; once StyleSizes gave them their own
                    // size, the multipliers scaled them a second time and ioslarge came out
                    // 336x307 - a clock twice the size of a lock screen's.

                    int contentW = (int)Math.Ceiling(Math.Max(timeSize2.Width, labelSize2.Width));
                    int contentH = (int)Math.Ceiling(timeSize2.Height)
                                   + (labelSize2.Height > 0 ? (int)Math.Ceiling(labelSize2.Height) + (int)(3 * scale) : 0);

                    // iosstack puts the date ABOVE the time, the way the iOS lock screen
                    // stacks its widgets: a small line, then the big figure.
                    if (style == "iosstack" && labelSize2.Height > 0)
                    {
                        contentH = (int)Math.Ceiling(labelSize2.Height) + (int)(6 * scale)
                                   + (int)Math.Ceiling(timeSize2.Height);
                    }

                    if (round)
                    {
                        int side = style == "analog"
                            ? (int)(86 * scale)
                            : Math.Max(contentW, contentH) + (int)(10 * scale);
                        contentW = side;
                        contentH = side;
                    }

                    int width = contentW + inset * 2 + ringPad * 2;
                    int height = contentH + inset * 2 + ringPad * 2;

                    // A little slack so the shadow is not clipped at the edges. A round style
                    // gets the same slack on both axes, or the square it just computed stops
                    // being square.
                    width += (int)(12 * scale);
                    height += (int)((round ? 12 : 10) * scale);

                    Rectangle bounds = Place(width, height, config);
                    if (Bounds != bounds) Bounds = bounds;
                    if (width != lastWidth || height != lastHeight)
                    {
                        lastWidth = width; lastHeight = height;
                    }
                    PaintToLayeredWindow(config, style, scale);
                }
            }

            /// <summary>
            /// The clock and label size for a style, at a given scale.
            ///
            /// One place, used twice: by the measurement that sizes the window and by the
            /// paint that draws into it. Keeping them apart is what produced every style at
            /// 181px wide with the clock clipped - the window was measured at 30px and the
            /// clock drawn at 62px.
            /// </summary>
            private static void StyleSizes(string style, float scale,
                                           out float timeSize, out float labelSize)
            {
                timeSize = 30f * scale;
                labelSize = 11f * scale;
                if (style == "bold") { timeSize = 38f * scale; labelSize = 12.5f * scale; }
                if (style == "ioslarge") { timeSize = 62f * scale; labelSize = 14f * scale; }
                if (style == "ioslight") { timeSize = 44f * scale; labelSize = 12f * scale; }
                if (style == "iosstack") { timeSize = 40f * scale; labelSize = 13f * scale; }
                if (style == "iosdate") { timeSize = 34f * scale; labelSize = 15f * scale; }
            }

            private static string Style(TimerConfig config)
            {
                string style = (config.Style ?? "").Trim().ToLowerInvariant();
                string[] known =
                {
                    "minimal", "glass", "card", "ring", "analog", "bold",
                    // iOS lock screen family. The request was "design timernya jelek cari
                    // kek timer apa gitutuh aku kasi prefrensi lockscreen time ios jiplak
                    // itu kasih beberapa pilihan dan background transparan ya".
                    "ioslarge", "ioslight", "iosstack", "iosdate",
                };
                foreach (string s in known) if (style == s) return s;
                return "minimal";
            }

            /// <summary>
            /// The face font.
            ///
            /// macOS and iOS use SF Pro, which is not on Windows. The closest thing that is
            /// installed everywhere this runs is Segoe UI Variable Display - the Windows 11
            /// face - and below that plain Segoe UI. Both are geometric humanist sans with
            /// figures that sit on the same width, which is what stops a countdown from
            /// jittering sideways as the digits change.
            ///
            /// The style changes the weight rather than the family: macOS uses a light face
            /// for a big clock and a semibold one for a widget, and a bold face everywhere -
            /// which is what the first version did - is what made it look like a scoreboard.
            /// </summary>
            private static Font TimeFont(float size, string style)
            {
                FontFamily family = PickFont();
                // macOS uses a light face for a big clock and a semibold one for a widget.
                // Bold everywhere - which is what the first version did - is what made it
                // look like a scoreboard.
                FontStyle weight = FontStyle.Regular;
                if (style == "card") weight = FontStyle.Bold;
                if (style == "bold") weight = FontStyle.Bold;

                // The iOS lock screen clock is not bold - it is a large, tightly tracked
                // face where the WEIGHT is low and the SIZE does the work. A bold face at
                // that size reads as a scoreboard, which is the "design timernya jelek"
                // complaint. Light is used where the family provides it.
                if (style == "ioslarge" || style == "ioslight" || style == "iosstack")
                {
                    foreach (FontFamily light in LightFamilies())
                    {
                        if (light.Name == family.Name || light.Name.StartsWith("Segoe UI Light"))
                            return new Font(light, size, FontStyle.Regular, GraphicsUnit.Pixel);
                    }
                    return new Font(family, size, FontStyle.Regular, GraphicsUnit.Pixel);
                }
                return new Font(family, size, weight, GraphicsUnit.Pixel);
            }

            /// <summary>
            /// The light faces that exist on Windows, best first.
            ///
            /// iOS uses SF Pro, which is not here. The closest match for a lock-screen clock
            /// is a light humanist sans: Segoe UI Light on Windows 10, and Segoe UI Variable
            /// Light on 11. Both keep the counters open at large sizes, which is what stops
            /// a 60px clock from looking like a block.
            /// </summary>
            private static FontFamily[] LightFamilies()
            {
                string[] names =
                {
                    "Segoe UI Variable Light",
                    "Segoe UI Variable Display Light",
                    "Segoe UI Light",
                    "Segoe UI Semilight",
                };
                var list = new List<FontFamily>();
                foreach (string name in names)
                {
                    try { list.Add(new FontFamily(name)); } catch { }
                }
                if (list.Count == 0) list.Add(PickFont());
                return list.ToArray();
            }

            private static Font LabelFont(float size)
            {
                return new Font(PickFont(), size, FontStyle.Regular, GraphicsUnit.Pixel);
            }

            private static FontFamily PickFont()
            {
                string[] preferred =
                {
                    "Segoe UI Variable Display",
                    "Segoe UI Variable Text",
                    "Segoe UI",
                    "Arial",
                };
                foreach (string name in preferred)
                {
                    try
                    {
                        var family = new FontFamily(name);
                        return family;
                    }
                    catch { }
                }
                return FontFamily.GenericSansSerif;
            }

            /// <summary>
            /// Where the widget sits, from the named position plus the user's offset.
            /// </summary>
            private static Rectangle Place(int width, int height, TimerConfig config)
            {
                Rectangle area = Screen.PrimaryScreen.WorkingArea;
                int left = area.Left + (area.Width - width) / 2;
                int top = area.Top + (area.Height - height) / 2;

                string position = string.IsNullOrEmpty(config.Position) ? "top-right" : config.Position;
                if (position.StartsWith("top", StringComparison.Ordinal)) top = area.Top + config.OffsetY;
                else if (position.StartsWith("bottom", StringComparison.Ordinal)) top = area.Bottom - height - config.OffsetY;
                else top = area.Top + (area.Height - height) / 2 + config.OffsetY;

                if (position.EndsWith("left", StringComparison.Ordinal)) left = area.Left + config.OffsetX;
                else if (position.EndsWith("right", StringComparison.Ordinal)) left = area.Right - width - config.OffsetX;
                else left = area.Left + (area.Width - width) / 2 + config.OffsetX;

                return new Rectangle(left, top, width, height);
            }

            /// <summary>
            /// Draws one frame into a 32bpp ARGB bitmap and hands it to the compositor.
            ///
            /// This is where the widget stopped being a box. Everything is drawn with an
            /// explicit alpha, so the only pixels that are not transparent are the glyphs
            /// themselves, their shadow, and - for glass and card - a faint wash.
            /// </summary>
            private void PaintToLayeredWindow(TimerConfig config, string style, float scale)
            {
                int w = Math.Max(1, Width), h = Math.Max(1, Height);

                using (var bitmap = new Bitmap(w, h, PixelFormat.Format32bppArgb))
                {
                    DrawFrame(bitmap, config, style, scale);

                    // A preview run takes the bitmap instead of putting it on screen, so the
                    // checker measures the drawing rather than a screenshot of it.
                    //
                    // This exists because the first version of the preview was a SECOND
                    // implementation of the same layout, and the two disagreed: the preview
                    // drew ioslarge at 329x307 while the widget drew it at 353x167. A check
                    // built on the preview would then have been checking a drawing the user
                    // never sees. Sharing this method is what makes the measurement evidence.
                    if (PreviewSink != null)
                    {
                        PreviewSink(bitmap);
                        return;
                    }

                    PushToWindow(bitmap);
                }
            }

            /// <summary>
            /// Receives each painted frame instead of the screen, when set.
            ///
            /// Set only by the --render-timer mode. The drawing is not duplicated for the
            /// preview: DrawFrame is the same method the widget paints with.
            /// </summary>
            internal static Action<Bitmap> PreviewSink;

            /// <summary>
            /// Paints one frame into the bitmap. Shared by the widget and the preview.
            /// </summary>
            internal void DrawFrame(Bitmap bitmap, TimerConfig config, string style, float scale)
            {
                int w = bitmap.Width, h = bitmap.Height;
                {
                    using (var g = Graphics.FromImage(bitmap))
                    {
                        g.SmoothingMode = SmoothingMode.AntiAlias;
                        g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                        g.Clear(Color.Transparent);

                        Color ink = ParseColor(config.Accent, Color.White);
                        if (lastFinished)
                            ink = Color.FromArgb(ink.R, Math.Min((byte)255, (byte)(ink.G + 40)), ink.B);

                        var area = new Rectangle(0, 0, w, h);
                        var content = new Rectangle(
                            (int)(6 * scale) + (style == "card" ? (int)(20 * scale) : 0) + (style == "ring" ? (int)(20 * scale) : 0),
                            (int)(5 * scale) + (style == "card" ? (int)(20 * scale) : 0) + (style == "ring" ? (int)(20 * scale) : 0),
                            w - (int)(12 * scale) - (style == "card" ? (int)(40 * scale) : 0) - (style == "ring" ? (int)(40 * scale) : 0),
                            h - (int)(10 * scale) - (style == "card" ? (int)(40 * scale) : 0) - (style == "ring" ? (int)(40 * scale) : 0));

                        // ── the wash behind the text, for glass and card ────────────────
                        if (style == "glass" || style == "card")
                        {
                            // A faint dark wash, not a slab. macOS widget material is dark
                            // and barely visible: it separates the text from a busy
                            // wallpaper without becoming an object of its own.
                            int alpha = style == "card" ? 96 : 54;
                            using (var brush = new SolidBrush(Color.FromArgb(alpha, 12, 14, 18)))
                            using (var path = RoundedRect(area, style == "card" ? (int)(18 * scale) : h / 2))
                            {
                                g.FillPath(brush, path);
                            }
                        }

                        // ── the ring, for the iOS-timer style ──────────────────────────
                        if (style == "ring")
                        {
                            // iOS Activity rings are thick: at 30% of the radius they read
                            // as a ring, while a hairline reads as a drawn circle. 3.5px was
                            // the hairline - the stroke is a share of the face now.
                            float radius = Math.Min(w, h) / 2f;
                            float thickness = Math.Max(3f, radius * 0.30f);
                            float pad = thickness / 2f + 1f;
                            var circle = new RectangleF(pad, pad, w - pad * 2, h - pad * 2);
                            using (var track = new Pen(Color.FromArgb(48, 255, 255, 255), thickness))
                            {
                                g.DrawEllipse(track, circle);
                            }
                            using (var arc = new Pen(Color.FromArgb(235, ink), thickness))
                            {
                                arc.StartCap = LineCap.Round;
                                arc.EndCap = LineCap.Round;
                                float sweep = (float)(lastProgress * 360.0);
                                if (sweep > 0.5f)
                                    g.DrawArc(arc, circle, -90, sweep);
                            }
                        }

                        // ── the analog dial, for the iOS Clock style ───────────────────
                        if (style == "analog")
                        {
                            DrawAnalogDial(g, w, h, ink, scale);
                        }

                        // ── the time ───────────────────────────────────────────────────
                        //
                        // Skipped for the analog dial: the hands are the reading, and
                        // drawing "19:31" under them would be a clock with a caption.
                        float timeSize = 30f * scale;
                        float labelSize = 11f * scale;

                        // The iOS lock screen clock is large by design - the size IS the
                        // style. ioslarge matches the real lock screen; ioslight is the same
                        // face a step down; iosstack is the widget form.
                        //
                        // Read from StyleSizes so the size used to DRAW and the size used to
                        // MEASURE are the same numbers. They were separate, and the widget was
                        // sized for one and drawn with the other.
                        StyleSizes(style, scale, out timeSize, out labelSize);

                        using (var family = PickFont())
                        using (var timeFont = TimeFont(timeSize, style))
                        using (var labelFont = LabelFont(labelSize))
                        using (var format = new StringFormat(StringFormat.GenericTypographic))
                        {
                            format.Alignment = StringAlignment.Center;
                            format.LineAlignment = StringAlignment.Center;

                            bool hasLabel = !string.IsNullOrEmpty(lastSubtitle) && style != "analog";
                            float timeH = timeFont.GetHeight(g);
                            float labelH = hasLabel ? labelFont.GetHeight(g) : 0f;
                            float gap = hasLabel ? 2f * scale : 0f;
                            float blockH = timeH + gap + labelH;

                            float cx = content.Left + content.Width / 2f;
                            float timeCy, labelY;
                            if (style == "iosstack" && hasLabel)
                            {
                                // Date first, then the time under it - the iOS lock screen
                                // widget stack. The block is centred as a whole.
                                labelY = content.Top + (content.Height - blockH) / 2f;
                                timeCy = labelY + labelH + gap + timeH / 2f;
                            }
                            else
                            {
                                timeCy = content.Top + (content.Height - blockH) / 2f + timeH / 2f;
                                labelY = timeCy + timeH / 2f + gap;
                            }
                            // The text boxes get vertical slack on purpose.
                            //
                            // A rectangle whose height is EXACTLY the font's height makes GDI+
                            // draw nothing at all: no exception, no warning, zero pixels. It is
                            // why the timer "sometimes did not appear" - the big iOS faces
                            // (ioslarge at 93px, ioslight at 66px) hit it while the small ones
                            // did not. Measured with ProbeRect: exactly font-high drew 0 pixels,
                            // 4px taller drew 1986.
                            //
                            // The slack is generous because the failure is silent and the cost
                            // is a few transparent pixels.
                            float timeSlack = timeH * 0.35f;
                            float labelSlack = labelH * 0.35f;
                            var timeRect = new RectangleF(content.Left, timeCy - timeH / 2f - timeSlack / 2f,
                                                          content.Width, timeH + timeSlack);
                            var labelRect = new RectangleF(content.Left, labelY - labelSlack / 2f,
                                                           content.Width, labelH + labelSlack);

                            int inkAlpha = lastDim ? 150 : 255;

                            // The shadow is what makes a background-less widget legible.
                            // Without it a white clock on a pale wallpaper disappears, and
                            // that is the whole reason the first version drew a box.
                            if (style != "analog")
                            {
                                DrawShadowedText(g, lastText, timeFont, timeRect, format, ink, inkAlpha, scale);

                                if (hasLabel)
                                {
                                    // The label is muted, the way a widget's caption is: it is
                                    // there to be read second. The iOS lock screen date is
                                    // dimmer than the clock and set in a wider face.
                                    Color label = Color.FromArgb(inkAlpha * 72 / 100, ink);
                                    DrawShadowedText(g, lastSubtitle, labelFont, labelRect, format, label, inkAlpha, scale * 0.7f);
                                }
                            }
                        }
                    }
                }
            }

            /// <summary>
            /// The iOS Clock face: a thin ring, twelve hour ticks, and two hands.
            ///
            /// This is the one style that draws no text, because the clock is the text. It
            /// follows the iOS Clock app: a hairline outer ring, ticks that are longer at
            /// the quarters, a tapered hour hand and a longer minute hand, and a small cap
            /// where they meet. Nothing else - no numbers, no second hand, no bezel.
            ///
            /// The hands are drawn as tapered polygons rather than lines, because a line
            /// with a round cap looks like a stick at these sizes while a taper reads as a
            /// hand.
            /// </summary>
            private static void DrawAnalogDial(Graphics g, int w, int h, Color ink, float scale)
            {
                float cx = w / 2f, cy = h / 2f;
                float radius = Math.Min(w, h) / 2f - Math.Max(3f, 5f * scale);

                // The hairline ring.
                using (var ring = new Pen(Color.FromArgb(90, ink), Math.Max(1f, 1.4f * scale)))
                {
                    g.DrawEllipse(ring, cx - radius, cy - radius, radius * 2, radius * 2);
                }

                // Twelve ticks, longer at the quarters - the iOS Clock arrangement.
                for (int i = 0; i < 12; i++)
                {
                    double angle = Math.PI * 2 * i / 12.0 - Math.PI / 2;
                    bool quarter = (i % 3) == 0;
                    float inner = radius - (quarter ? 7f : 4f) * scale;
                    float outer = radius - 1.5f * scale;
                    var a = new PointF(cx + (float)Math.Cos(angle) * inner,
                                       cy + (float)Math.Sin(angle) * inner);
                    var b = new PointF(cx + (float)Math.Cos(angle) * outer,
                                       cy + (float)Math.Sin(angle) * outer);
                    using (var pen = new Pen(Color.FromArgb(quarter ? 230 : 130, ink),
                                             Math.Max(1f, (quarter ? 2f : 1.2f) * scale)))
                    {
                        pen.StartCap = LineCap.Round;
                        pen.EndCap = LineCap.Round;
                        g.DrawLine(pen, a, b);
                    }
                }

                DateTime now = DateTime.Now;
                double hourAngle = (now.Hour % 12 + now.Minute / 60.0) * 30.0 - 90.0;
                double minuteAngle = now.Minute * 6.0 - 90.0;

                DrawHand(g, cx, cy, hourAngle, radius * 0.52f, 4.2f * scale, ink);
                DrawHand(g, cx, cy, minuteAngle, radius * 0.78f, 3.0f * scale, ink);

                // The cap at the pivot.
                float cap = 2.6f * scale;
                using (var brush = new SolidBrush(Color.FromArgb(240, ink)))
                {
                    g.FillEllipse(brush, cx - cap, cy - cap, cap * 2, cap * 2);
                }
            }

            /// <summary>One hand: a tapered triangle from the pivot, with a small tail.</summary>
            private static void DrawHand(Graphics g, float cx, float cy, double angleDeg,
                                         float length, float width, Color ink)
            {
                double a = angleDeg * Math.PI / 180.0;
                float dx = (float)Math.Cos(a), dy = (float)Math.Sin(a);
                // Perpendicular, for the width of the base.
                float px = -dy, py = dx;
                float tail = length * 0.18f;

                var tip = new PointF(cx + dx * length, cy + dy * length);
                var left = new PointF(cx + px * width / 2f - dx * tail, cy + py * width / 2f - dy * tail);
                var right = new PointF(cx - px * width / 2f - dx * tail, cy - py * width / 2f - dy * tail);

                using (var brush = new SolidBrush(Color.FromArgb(240, ink)))
                {
                    g.FillPolygon(brush, new[] { tip, left, right });
                }
            }

            /// <summary>
            /// Draws text with a soft shadow so it stays readable on any wallpaper.
            ///
            /// A real Gaussian blur of the glyphs would be better but costs a second bitmap
            /// and a convolution on every tick. This draws the glyphs eight times around the
            /// centre at low alpha and then the glyph itself on top, which produces a halo
            /// that is indistinguishable at these sizes and costs one extra pass.
            /// </summary>
            private static void DrawShadowedText(Graphics g, string text, Font font, RectangleF rect,
                                                 StringFormat format, Color colour, int alpha, float scale)
            {
                float radius = Math.Max(1.2f, 1.6f * scale);
                int shadowAlpha = Math.Min(150, Math.Max(60, (int)(90 * Math.Min(1.6f, scale))));

                using (var shadow = new SolidBrush(Color.FromArgb(shadowAlpha, 0, 0, 0)))
                {
                    for (int i = 0; i < 8; i++)
                    {
                        double angle = Math.PI * 2 * i / 8.0;
                        var offset = new RectangleF(
                            rect.X + (float)(Math.Cos(angle) * radius),
                            rect.Y + (float)(Math.Sin(angle) * radius),
                            rect.Width, rect.Height);
                        g.DrawString(text, font, shadow, offset, format);
                    }
                    // A second, tighter pass darkens the immediate edge, which is what makes
                    // the halo read as a shadow rather than as a blur.
                    var near = new RectangleF(rect.X, rect.Y + radius * 0.7f, rect.Width, rect.Height);
                    g.DrawString(text, font, shadow, near, format);
                }

                using (var brush = new SolidBrush(Color.FromArgb(alpha, colour)))
                {
                    g.DrawString(text, font, brush, rect, format);
                }
            }

            private static GraphicsPath RoundedRect(Rectangle area, int radius)
            {
                var path = new GraphicsPath();
                Rectangle r = new Rectangle(area.X, area.Y, Math.Max(1, area.Width - 1), Math.Max(1, area.Height - 1));
                int limit = Math.Min(r.Width, r.Height) / 2;
                int use = Math.Max(0, Math.Min(radius, limit));
                if (use == 0)
                {
                    path.AddRectangle(r);
                    return path;
                }
                path.AddArc(r.X, r.Y, use * 2, use * 2, 180, 90);
                path.AddArc(r.Right - use * 2, r.Y, use * 2, use * 2, 270, 90);
                path.AddArc(r.Right - use * 2, r.Bottom - use * 2, use * 2, use * 2, 0, 90);
                path.AddArc(r.X, r.Bottom - use * 2, use * 2, use * 2, 90, 90);
                path.CloseFigure();
                return path;
            }

            /// <summary>
            /// Hands the finished bitmap to the compositor with its alpha channel intact.
            ///
            /// UpdateLayeredWindow takes the bitmap as the window's whole appearance: the
            /// alpha byte of each pixel is its opacity. That is what allows an opaque glyph
            /// next to a fully transparent pixel, with a smooth edge between them.
            /// </summary>
            private void PushToWindow(Bitmap bitmap)
            {
                IntPtr screenDc = GetDC(IntPtr.Zero);
                IntPtr memDc = CreateCompatibleDC(screenDc);
                IntPtr hBitmap = IntPtr.Zero;
                IntPtr oldBitmap = IntPtr.Zero;
                try
                {
                    hBitmap = bitmap.GetHbitmap(Color.FromArgb(0));
                    oldBitmap = SelectObject(memDc, hBitmap);

                    var size = new SIZE { cx = bitmap.Width, cy = bitmap.Height };
                    var src = new POINT { X = 0, Y = 0 };
                    var dst = new POINT { X = Left, Y = Top };
                    var blend = new BLENDFUNCTION
                    {
                        BlendOp = AC_SRC_OVER,
                        BlendFlags = 0,
                        SourceConstantAlpha = 255,
                        AlphaFormat = AC_SRC_ALPHA,
                    };

                    UpdateLayeredWindow(Handle, screenDc, ref dst, ref size,
                                        memDc, ref src, 0, ref blend, ULW_ALPHA);
                }
                finally
                {
                    if (oldBitmap != IntPtr.Zero) SelectObject(memDc, oldBitmap);
                    if (hBitmap != IntPtr.Zero) DeleteObject(hBitmap);
                    DeleteDC(memDc);
                    ReleaseDC(IntPtr.Zero, screenDc);
                }
            }

            private static Color ParseColor(string value, Color fallback)
            {
                if (string.IsNullOrWhiteSpace(value)) return fallback;
                try
                {
                    Color parsed = ColorTranslator.FromHtml(value.Trim());
                    return parsed;
                }
                catch { return fallback; }
            }
        }
    }
}
