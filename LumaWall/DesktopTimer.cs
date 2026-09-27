// DesktopTimer.cs - the always-on-top timer that sits on the wallpaper.
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

using System;
using System.Drawing;
using System.Drawing.Drawing2D;
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
    /// Shape, size and position come from the config because the right answer depends on
    /// the wallpaper behind it - a bright wallpaper needs a different treatment from a dark
    /// one, and the empty corner is different on every desktop.
    /// </summary>
    internal sealed class DesktopTimer : IDisposable
    {
        private readonly TimerWindow window;
        private readonly System.Windows.Forms.Timer tick;
        private readonly Func<TimerConfig> config;
        private DateTime anchor = DateTime.UtcNow;
        private bool disposed;

        // The countdown's remaining time is derived from a start instant rather than
        // decremented, so a tick that arrives late - after a game hitched, or after the
        // machine slept - cannot make the timer drift slow.
        private TimeSpan remaining;
        private bool running;

        public DesktopTimer(Func<TimerConfig> configSource)
        {
            config = configSource;
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
            window.Show();
            tick.Start();
            Render();
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
            if (!window.Visible) { window.Show(); tick.Start(); }
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

        /// <summary>
        /// Paints the window with what the timer currently reads.
        ///
        /// The text is measured before the window is sized, so the shape grows to fit the
        /// digits rather than clipping them - which is what happens when a countdown drops
        /// from 10:00 to 9:59 and the face was sized for the longer string.
        /// </summary>
        private void Render()
        {
            if (disposed) return;
            TimerConfig current = config();
            if (current == null || !current.Enabled) { Stop(); return; }

            TimeSpan value = Remaining();
            string text = Format(value, current);

            bool finished = current.Mode == "countdown" && value <= TimeSpan.Zero;
            // A countdown that reaches zero blinks, because a silent 00:00 on a desktop the
            // user is not looking at is not a notification.
            bool dim = finished && current.BlinkAtEnd && ((DateTime.UtcNow.Millisecond / 500) % 2 == 0);

            window.Draw(text, current, finished, dim);
        }

        private static string Format(TimeSpan value, TimerConfig current)
        {
            if (current.Mode == "clock")
            {
                DateTime now = DateTime.Now;
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
        /// The window itself. A layered window rather than a WPF one, because the desktop
        /// timer must not appear in Alt-Tab, must not take focus, and must let clicks
        /// through to whatever is underneath.
        /// </summary>
        private sealed class TimerWindow : Form
        {
            private const int WS_EX_LAYERED = 0x00080000;
            private const int WS_EX_TRANSPARENT = 0x00000020;
            private const int WS_EX_TOOLWINDOW = 0x00000080;
            private const int WS_EX_NOACTIVATE = 0x08000000;
            private const int SW_SHOWNOACTIVATE = 4;

            [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int command);

            private TimerConfig current = new TimerConfig();
            private string lastText = "";
            private bool lastFinished;
            private bool lastDim;

            public TimerWindow()
            {
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                // The window is never activated, so it must not try to be a normal window:
                // no close box, no minimise, no focus.
                TopMost = true;
                BackColor = Color.Black;
                DoubleBuffered = true;
                SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint
                    | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
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

            public void Apply(TimerConfig value)
            {
                current = value ?? new TimerConfig();
                Opacity = Math.Max(0.2, Math.Min(1.0, current.Opacity));
            }

            /// <summary>
            /// Sizes and paints the face for one reading.
            ///
            /// Everything is derived from the current text, so a shape that fits "10:00"
            /// also fits "9:59" and a clock that grows from "09:59" to "10:00" grows the
            /// window instead of clipping the digit.
            /// </summary>
            public void Draw(string text, TimerConfig config, bool finished, bool dim)
            {
                // Skip a repaint when nothing visible changed. At 5 Hz a clock would
                // otherwise redraw 5 times a second for no reason, and each redraw is a
                // window resize plus a full paint.
                if (text == lastText && finished == lastFinished && dim == lastDim) return;
                lastText = text; lastFinished = finished; lastDim = dim;

                using (var probe = CreateGraphics())
                {
                    float scale = Math.Max(50, Math.Min(250, config.Scale)) / 100f;
                    using (var family = PickFont())
                    {
                        using (var font = new Font(family, 30f * scale, FontStyle.Bold, GraphicsUnit.Pixel))
                        {
                            SizeF measured = probe.MeasureString(text, font);
                            int padding = config.Shape == "bare" ? (int)(6 * scale) : (int)(26 * scale);
                            int width = (int)Math.Ceiling(measured.Width) + padding * 2;
                            int height = (int)Math.Ceiling(measured.Height) + (int)(14 * scale) * 2;

                            if (config.Shape == "circle")
                            {
                                // A circle has to be big enough for the text in both
                                // directions, so the larger of the two wins.
                                int side = Math.Max(width, height);
                                width = side; height = side;
                            }
                            else if (config.Shape == "square")
                            {
                                int side = Math.Max(width, height);
                                width = side; height = side;
                            }

                            Rectangle bounds = Place(width, height, config);
                            if (Bounds != bounds) Bounds = bounds;
                            Invalidate();
                        }
                    }
                }
            }

            private static FontFamily PickFont()
            {
                // A font that exists everywhere, chosen for digits that stay distinguishable
                // at a glance: Segoe UI's tabular figures keep a countdown from jittering as
                // the digits change.
                string[] preferred = { "Segoe UI", "Segoe UI Semibold", "Arial", "Tahoma" };
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
            /// Where the face sits, from the named position plus the user's offset.
            ///
            /// The window is placed on the primary screen's working area unless the chosen
            /// corner belongs to another screen - the offset is applied after the corner, so
            /// a positive X always moves it toward the right regardless of which corner it
            /// started from.
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

            protected override void OnPaint(PaintEventArgs e)
            {
                Graphics g = e.Graphics;
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;

                Color face = ParseColor(current.Face, Color.FromArgb(11, 14, 20));
                Color accent = ParseColor(current.Accent, Color.FromArgb(125, 211, 252));
                if (lastFinished) accent = Color.FromArgb(accent.R, Math.Min((byte)255, (byte)(accent.G + 40)), accent.B);

                Rectangle area = new Rectangle(0, 0, Width, Height);
                float scale = Math.Max(50, Math.Min(250, current.Scale)) / 100f;

                if (current.Shape != "bare")
                {
                    using (var brush = new SolidBrush(Color.FromArgb(lastDim ? 150 : 235, face)))
                    using (var path = ShapePath(area, current.Shape, (int)(14 * scale)))
                    {
                        g.FillPath(brush, path);
                    }
                    // A hairline of the accent colour, so the widget reads as part of the
                    // app rather than as a stray system dialog.
                    using (var pen = new Pen(Color.FromArgb(150, accent), Math.Max(1f, 1.5f * scale)))
                    using (var path = ShapePath(area, current.Shape, (int)(14 * scale)))
                    {
                        var inset = new RectangleF(path.GetBounds().X + 1, path.GetBounds().Y + 1,
                            path.GetBounds().Width - 2, path.GetBounds().Height - 2);
                        using (var edge = ShapePath(Rectangle.Round(inset), current.Shape, (int)(14 * scale)))
                            g.DrawPath(pen, edge);
                    }
                }

                using (var family = PickFont())
                using (var font = new Font(family, 30f * scale, FontStyle.Bold, GraphicsUnit.Pixel))
                using (var textBrush = new SolidBrush(lastDim ? Color.FromArgb(140, accent) : accent))
                using (var format = new StringFormat())
                {
                    format.Alignment = StringAlignment.Center;
                    format.LineAlignment = StringAlignment.Center;
                    g.DrawString(lastText, font, textBrush, area, format);
                }
            }

            private static GraphicsPath ShapePath(Rectangle area, string shape, int radius)
            {
                var path = new GraphicsPath();
                Rectangle r = new Rectangle(area.X, area.Y, Math.Max(1, area.Width - 1), Math.Max(1, area.Height - 1));
                if (shape == "circle")
                {
                    path.AddEllipse(r);
                }
                else if (shape == "square")
                {
                    path.AddRectangle(r);
                }
                else
                {
                    // Pill: a rounded rectangle whose radius is capped at half the shorter
                    // side, which is what keeps it a pill rather than a lozenge.
                    int limit = Math.Min(r.Width, r.Height) / 2;
                    int use = Math.Min(radius, limit);
                    path.AddArc(r.X, r.Y, use * 2, use * 2, 180, 90);
                    path.AddArc(r.Right - use * 2, r.Y, use * 2, use * 2, 270, 90);
                    path.AddArc(r.Right - use * 2, r.Bottom - use * 2, use * 2, use * 2, 0, 90);
                    path.AddArc(r.X, r.Bottom - use * 2, use * 2, use * 2, 90, 90);
                    path.CloseFigure();
                }
                return path;
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
