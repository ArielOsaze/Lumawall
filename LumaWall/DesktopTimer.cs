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
            // Gaya iOS TIDAK PERNAH menampilkan detik.
            //
            // Jam layar kunci iOS menunjukkan jam dan menit saja, dan itu
            // bukan detail kecil: menambahkan detik mengubahnya dari jam
            // menjadi pengukur waktu. Detik yang berubah setiap saat juga
            // menarik mata ke widget terus-menerus, yang justru kebalikan
            // dari gunanya jam layar kunci.
            //
            // Pilihan ShowSeconds milik pengguna tetap dihormati untuk gaya
            // lain, karena di sana ia memang masuk akal - stopwatch, timer,
            // dan papan skor memang perlu detik.
            bool gayaIos = current.Style == "ioslarge" || current.Style == "ioslight"
                || current.Style == "iosstack" || current.Style == "iosdate";
            bool pakaiDetik = current.ShowSeconds && !gayaIos;

            if (current.Mode == "clock")
            {
                DateTime now = DateTime.Now;
                if (current.TwelveHour)
                {
                    // No leading zero, the way macOS and iOS show a clock: "9:41", not
                    // "09:41". The leading zero makes a desktop clock look like a log line.
                    string format = pakaiDetik ? "h:mm:ss" : "h:mm";
                    return now.ToString(format, CultureInfo.InvariantCulture);
                }
                return pakaiDetik
                    ? now.ToString("HH:mm:ss", CultureInfo.InvariantCulture)
                    : now.ToString("HH:mm", CultureInfo.InvariantCulture);
            }

            if (value < TimeSpan.Zero) value = TimeSpan.Zero;
            int hours = (int)value.TotalHours;
            if (hours > 0)
                return pakaiDetik
                    ? string.Format(CultureInfo.InvariantCulture, "{0}:{1:00}:{2:00}", hours, value.Minutes, value.Seconds)
                    : string.Format(CultureInfo.InvariantCulture, "{0}:{1:00}", hours, value.Minutes);
            return pakaiDetik
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

                // Gaya iOS: ukurannya yang membuatnya terbaca sebagai iOS.
                //
                // Jam lock screen iPhone tingginya sekitar 11% dari tinggi layar,
                // dan itu membuatnya jadi unsur paling besar di layar - bukan
                // hiasan kecil di sudut. Angka-angka di bawah disetel dari
                // perbandingan itu: pada monitor 1080p, ioslarge tergambar
                // sekitar 120px, dan seluruh blok tanggal+jam mengisi sekitar
                // seperlima tinggi layar.
                //
                // Yang membuatnya terlihat seperti iOS bukan hanya ukurannya,
                // tetapi PERBANDINGANNYA: jam yang sangat besar dengan tanggal
                // kecil di atasnya. Jam besar dengan tanggal yang ikut membesar
                // akan terbaca sebagai dua teks biasa, bukan sebagai jam.
                if (style == "ioslarge") { timeSize = 80f * scale; labelSize = 15f * scale; }

                // ioslight, iosstack, iosdate: jam harus tetap DOMINAN.
                //
                // Di lock screen iPhone, jam selalu jauh lebih besar daripada
                // tanggalnya - itulah yang membuatnya terbaca sebagai jam, bukan
                // sebagai dua baris teks. Ukuran 58/52/46 hanya dua sampai tiga
                // kali ukuran tanggalnya, dan pada perbandingan itu jamnya
                // terbaca sebagai teks biasa yang kebetulan lebih besar.
                //
                // Yang juga penting adalah BERAT hurufnya: iOS memakai berat
                // paling tipis untuk jamnya. Huruf yang lebih tebal pada ukuran
                // besar terlihat berat, dan itu bagian dari "kayak bukan iOS".
                if (style == "ioslight") { timeSize = 68f * scale; labelSize = 13f * scale; }
                if (style == "iosstack") { timeSize = 64f * scale; labelSize = 13f * scale; }
                if (style == "iosdate") { timeSize = 60f * scale; labelSize = 13f * scale; }
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
            /// <summary>
            /// The face for a style, at a given size.
            ///
            /// Every style gets a face that is actually different, and the difference is
            /// measured rather than assumed. Stroke weight, as the share of dark pixels in a
            /// 62px "9:41" rendered on white:
            ///
            ///   Segoe UI Variable Display Light    0.7%   (122px wide)
            ///   Segoe UI Light                     1.1%   (124px)
            ///   Segoe UI Variable Display Semil    1.2%   (124px)
            ///   Segoe UI Semilight                 1.4%   (127px)
            ///   Segoe UI Variable Display          1.8%   (127px)
            ///   Segoe UI                           1.8%   (138px)
            ///
            /// That table is the whole point. The iOS styles used to ask for a light face with
            // a condition that could never match it:
            ///
            ///   if (light.Name == family.Name || light.Name.StartsWith("Segoe UI Light"))
            //       return new Font(light, ...);
            //   }
            //   return new Font(family, ...);   // regular
            ///
            /// LightFamilies() is ordered best-first, so the first entry is
            /// "Segoe UI Variable Display Light" - and that name is neither equal to
            /// "Segoe UI Variable Display" nor does it start with "Segoe UI Light". The test
            /// skipped the thin face and fell through to "Segoe UI Light", 57% heavier, or to
            /// the regular face. iosdate was not in the list at all, so it drew in exactly the
            /// same font as minimal - which is what "font timernya gada bedanya" was.
            ///
            /// Now the face is named per style and the first available match is used, so a
            /// style cannot silently fall back to a heavier face.
            /// </summary>
            /// <summary>
            /// Jembatan untuk alat uji render.
            ///
            /// `TimeFont` bersifat private karena hanya jendela jam yang boleh
            /// memakainya. Alat uji render perlu memakai font yang SAMA PERSIS,
            /// karena kalau ia memilih fontnya sendiri, gambar yang dihasilkan
            /// tidak membuktikan apa pun tentang jam yang ada di desktop.
            /// </summary>
            internal static Font TimeFontUntukUji(float size, string style)
            {
                return TimeFont(size, style);
            }

            private static Font TimeFont(float size, string style)
            {
                Face[] faces = FacesFor(style);

                foreach (Face face in faces)
                {
                    // Lewat FontLoader, bukan `new FontFamily(nama)`.
                    //
                    // `new FontFamily(nama)` hanya melihat font yang terpasang
                    // di sistem dan TIDAK melihat koleksi font yang dibundel.
                    // Memakai bentuk itu di sini berarti setiap nama Inter
                    // melempar, setiap percobaan jatuh ke cadangan, dan timer
                    // selalu menggambar dengan Segoe - sementara log melaporkan
                    // font berhasil dimuat. Itu penyebab "fontnya masih basic".
                    var family = FontLoader.AmbilDariKoleksi(face.Family);
                    if (family != null)
                    {
                        try { return new Font(family, size, face.Style, GraphicsUnit.Pixel); }
                        catch { }
                    }

                    // Cadangan ke font sistem, untuk nama yang memang bukan milik
                    // koleksi (Segoe) atau kalau Inter tidak ada.
                    try
                    {
                        return new Font(new FontFamily(face.Family), size, face.Style, GraphicsUnit.Pixel);
                    }
                    catch { }
                }
                return new Font(PickFont(), size, FontStyle.Regular, GraphicsUnit.Pixel);
            }

            /// <summary>
            /// Pasangan (nama family, gaya) untuk satu gaya timer.
            ///
            /// Dipisah dari FacesFor karena keduanya harus cocok. Meminta
            /// FontStyle.Bold pada family yang sudah SemiBold membuat GDI+
            /// menyintesis bold di atas semibold - hurufnya jadi kabur dan
            /// gemuk di ukuran besar, dan itu terlihat jelas pada jam 62px.
            /// Yang benar adalah memilih face asli yang memang setebal itu.
            /// </summary>
            private struct Face
            {
                public string Family;
                public FontStyle Style;
                public Face(string family, FontStyle style) { Family = family; Style = style; }
            }

            /// <summary>
            /// The faces a style will accept, best first.
            ///
            /// Semua gaya memakai SATU keluarga font yang sama - Inter - dengan
            /// berat yang berbeda. Sebelumnya setiap gaya menamai face Segoe
            /// yang berbeda, sehingga hasilnya terlihat seperti beberapa font
            /// berbeda yang ditempel menjadi satu, bukan satu widget dengan satu
            /// suara.
            ///
            /// Inter dipilih karena bentuknya paling dekat dengan SF Pro milik
            /// iOS di antara font yang boleh dibundel: geometris, x-height
            /// tinggi, angka tabular yang lebarnya sama sehingga digit jam tidak
            /// bergeser saat menit berubah. Lisensinya (SIL OFL) mengizinkan
            /// dibundel bersama aplikasi komersial.
            ///
            /// Nama-nama Segoe tetap ada sebagai cadangan terakhir: kalau
            /// pemuatan font gagal karena sebab apa pun, timer harus tetap
            /// tampil dengan font sistem, bukan gagal.
            /// </summary>
            private static Face[] FacesFor(string style)
            {
                switch (style)
                {
                    // iOS 15 lock screen: sangat besar dan sangat tipis.
                    //
                    // Memakai Inter DISPLAY, bukan Inter biasa.
                    //
                    // Inter punya dua varian dengan tujuan yang berbeda: "Inter"
                    // dirancang untuk teks kecil (hurufnya lebih lebar dan
                    // jaraknya lebih longgar supaya terbaca di badan paragraf),
                    // sedangkan "Inter Display" dirancang untuk ukuran BESAR
                    // (hurufnya lebih rapat dan proporsinya lebih halus). Itu
                    // pembagian yang sama dengan SF Pro Text dan SF Pro Display
                    // milik Apple - dan jam lock screen iPhone memakai yang
                    // Display.
                    //
                    // Memakai varian teks untuk jam 120px adalah salah satu
                    // sebab jamnya terlihat "seperti font biasa": hurufnya
                    // terlalu lebar dan jaraknya terlalu longgar untuk ukuran
                    // sebesar itu.
                    case "ioslarge":
                        return new[]
                        {
                            new Face("Inter Display Light", FontStyle.Regular),
                            new Face("Inter Display ExtraLight", FontStyle.Regular),
                            new Face("Inter Display", FontStyle.Regular),
                            new Face("Inter Light", FontStyle.Regular),
                            new Face("Segoe UI Variable Display Light", FontStyle.Regular),
                            new Face("Segoe UI Light", FontStyle.Regular),
                        };

                    // Satu langkah lebih tebal, supaya keduanya terlihat berbeda.
                    case "ioslight":
                        return new[]
                        {
                            new Face("Inter Display Light", FontStyle.Regular),
                            new Face("Inter Display ExtraLight", FontStyle.Regular),
                            new Face("Inter Light", FontStyle.Regular),
                            new Face("Segoe UI Variable Display Light", FontStyle.Regular),
                            new Face("Segoe UI Light", FontStyle.Regular),
                        };

                    // Widget bertumpuk: tipis, tetapi tanggal yang bekerja.
                    case "iosstack":
                        return new[]
                        {
                            new Face("Inter Display Light", FontStyle.Regular),
                            new Face("Inter Display ExtraLight", FontStyle.Regular),
                            new Face("Inter ExtraLight", FontStyle.Regular),
                            new Face("Segoe UI Variable Display Light", FontStyle.Regular),
                            new Face("Segoe UI", FontStyle.Regular),
                        };

                    // Gaya yang mengutamakan tanggal.
                    case "iosdate":
                        return new[]
                        {
                            new Face("Inter Display Light", FontStyle.Regular),
                            new Face("Inter Display ExtraLight", FontStyle.Regular),
                            new Face("Inter Light", FontStyle.Regular),
                            new Face("Segoe UI Variable Display Light", FontStyle.Regular),
                            new Face("Segoe UI", FontStyle.Regular),
                        };

                    // Papan skor: tebal dengan sengaja.
                    //
                    // "Inter" dengan FontStyle.Bold, bukan "Inter SemiBold"
                    // dengan Bold: yang kedua menyintesis bold di atas semibold
                    // dan hasilnya kabur. Family "Inter" sudah memuat face Bold
                    // asli dari Inter-Bold.ttf.
                    case "bold":
                        return new[]
                        {
                            new Face("Inter", FontStyle.Bold),
                            new Face("Inter SemiBold", FontStyle.Regular),
                            new Face("Segoe UI Variable Display", FontStyle.Bold),
                            new Face("Segoe UI", FontStyle.Bold),
                        };

                    // Kartu widget: semi tebal, karena lapisan di belakangnya
                    // memakan kontras. Face SemiBold asli, bukan bold sintetis.
                    case "card":
                        return new[]
                        {
                            new Face("Inter SemiBold", FontStyle.Regular),
                            new Face("Inter", FontStyle.Bold),
                            new Face("Segoe UI Variable Display", FontStyle.Bold),
                            new Face("Segoe UI", FontStyle.Bold),
                        };

                    default:
                        return new[]
                        {
                            new Face("Inter", FontStyle.Regular),
                            new Face("Inter Light", FontStyle.Regular),
                            new Face("Segoe UI Variable Display", FontStyle.Regular),
                            new Face("Segoe UI", FontStyle.Regular),
                        };
                }
            }

            /// <summary>
            /// The light faces that exist on this machine, best first.
            ///
            /// Kept for the analog dial and anything that needs a light face without naming a
            /// style. It returns the families that are actually installed, so a caller that
            /// takes the first entry cannot end up with a heavier face by accident.
            /// </summary>
            private static FontFamily[] LightFamilies()
            {
                string[] names =
                {
                    "Segoe UI Variable Display Light",
                    "Segoe UI Light",
                    "Segoe UI Variable Display Semil",
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

            /// <summary>
            /// Font tanggal - Inter, sama dengan jamnya.
            ///
            /// Sebelumnya fungsi ini memakai PickFont(), yang mencari font
            /// SISTEM (Segoe UI Variable Display, lalu Segoe UI). Akibatnya
            /// tanggal dan jam memakai dua font berbeda: jamnya Inter yang
            /// tipis dan geometris, tanggalnya Segoe yang lebih lebar dan
            /// bulat - dan mata langsung melihat keduanya tidak sekeluarga.
            ///
            /// Di lock screen iPhone, tanggal dan jam memang berbeda UKURAN dan
            /// KETEBALAN, tetapi keduanya font yang sama. Itu yang membuat
            /// keduanya terbaca sebagai satu blok, bukan sebagai dua teks yang
            /// kebetulan bertumpuk.
            ///
            /// Tanggal memakai Light, bukan Regular: pada ukuran kecil, Regular
            /// terlihat berat di sebelah jam yang tipis, dan iOS memakai berat
            /// yang lebih ringan untuk tanggalnya.
            /// </summary>
            private static Font LabelFont(float size)
            {
                foreach (string nama in new[] { "Inter Light", "Inter", "Segoe UI Variable Display Light", "Segoe UI" })
                {
                    var family = FontLoader.AmbilDariKoleksi(nama);
                    if (family != null)
                    {
                        try { return new Font(family, size, FontStyle.Regular, GraphicsUnit.Pixel); }
                        catch { }
                    }

                    // Font sistem dicoba di blok terpisah.
                    //
                    // Kalau `new FontFamily(nama)` gagal untuk nama pertama, ia
                    // melempar dan loop harus LANJUT ke nama berikutnya - bukan
                    // keluar. Melemparnya di dalam try yang sama dengan return
                    // membuat setiap kegagalan mengakhiri pencarian, sehingga
                    // satu nama yang tidak ada berarti tanggal selalu jatuh ke
                    // PickFont() dan kembali memakai Segoe.
                    try
                    {
                        return new Font(new FontFamily(nama), size, FontStyle.Regular, GraphicsUnit.Pixel);
                    }
                    catch { }
                }
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
                Rectangle area = ScreenFor(config).WorkingArea;
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
            /// The screen the widget belongs on: the one the config names, or the primary one.
            ///
            /// The named screen can go away - a monitor unplugged, or a config copied from
            /// another machine - and the widget must still appear somewhere rather than
            /// disappearing. Falling back to the primary screen is what the app did before
            /// the setting existed, so that is the fallback.
            /// </summary>
            private static Screen ScreenFor(TimerConfig config)
            {
                string wanted = config == null ? null : config.Monitor;
                if (!string.IsNullOrEmpty(wanted))
                {
                    foreach (Screen screen in Screen.AllScreens)
                    {
                        if (string.Equals(screen.DeviceName, wanted, StringComparison.OrdinalIgnoreCase))
                            return screen;
                    }
                }
                return Screen.PrimaryScreen;
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

                            // Jarak antara tanggal dan jam di lock screen iOS.
                            //
                            // Di iOS, tanggal duduk RAPAT di atas jam - bukan
                            // terpisah jauh. Jarak 2px yang lama membuat keduanya
                            // terbaca sebagai dua elemen terpisah, bukan sebagai
                            // satu blok tanggal-dan-jam seperti di iPhone.
                            float gap = hasLabel ? 4f * scale : 0f;
                            float blockH = timeH + gap + labelH;

                            float cx = content.Left + content.Width / 2f;
                            float timeCy, labelY;

                            // Tanggal SELALU di atas jam, untuk semua gaya iOS.
                            //
                            // Ini bukan pilihan gaya - ini susunan yang Apple
                            // pakai dan tidak bisa diubah pemakai: "The date
                            // always sits above the clock; nothing else on the
                            // lock screen is repositionable - Apple fixes the
                            // layout."
                            //
                            // Sebelumnya hanya iosstack yang menaruh tanggal di
                            // atas; ioslarge, ioslight, dan iosdate menaruhnya di
                            // BAWAH. Itu susunan yang tidak pernah ada di iPhone,
                            // dan itulah kenapa jamnya "ga kayak bener yg ios" -
                            // bukan karena fontnya, melainkan karena susunannya
                            // bukan susunan iOS.
                            bool tanggalDiAtas = style == "ioslarge" || style == "ioslight"
                                || style == "iosstack" || style == "iosdate";

                            if (tanggalDiAtas && hasLabel)
                            {
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
                            // Without it a white clock on a pale wallpaper disappears.
                            //
                            // Tetapi ukurannya harus berbeda per gaya. iOS menggambar jam
                            // layar kuncinya TANPA bayangan sama sekali - yang membuatnya
                            // terbaca adalah ketebalan hurufnya, bukan halo. Halo delapan
                            // arah di sekeliling huruf tipis justru membuatnya terlihat
                            // seperti huruf berongga: yang terbaca mata adalah bayangannya,
                            // bukan hurufnya, dan itu penyebab "kok kayak bukan iOS".
                            //
                            // Untuk gaya tipis besar, bayangannya dikurangi sampai hampir
                            // tidak ada. Untuk gaya tebal, bayangan tetap penuh karena di
                            // situ ia memang membantu dan tidak mengubah bentuk huruf.
                            if (style != "analog")
                            {
                                // Gaya tipis memakai bayangan RAPAT (skala 0), bukan halo.
                                //
                                // Ini bukan penyetelan halus - ini yang menentukan
                                // apakah jam terlihat seperti iOS atau tidak. Halo
                                // delapan arah di sekeliling huruf tipis 90px
                                // menghasilkan jam yang terbaca BERONGGA: yang
                                // terlihat adalah bayangannya, dan huruf aslinya
                                // hanya tampak sebagai garis tipis di tengahnya.
                                // Jam layar kunci iOS adalah huruf SOLID.
                                //
                                // Daftar gaya di sini harus memuat SEMUA gaya tipis.
                                // Sebelumnya "ioslight" tidak ada di daftar ini,
                                // sehingga gaya yang justru paling mirip iOS
                                // mendapat halo penuh - dan itulah gaya yang dipakai
                                // pengguna saat melaporkan "fontnya ga kayak iOS".
                                bool tipis = style == "ioslarge" || style == "ioslight"
                                    || style == "iosstack" || style == "iosdate"
                                    || style == "minimal" || style == "glass"
                                    || style == "thin" || style == "elegant"
                                    || style == "bold" || style == "card"
                                    || style == "ring";
                                float shadowSkala = tipis ? 0f : 1f;

                                DrawShadowedText(g, lastText, timeFont, timeRect, format, ink, inkAlpha,
                                                 scale, shadowSkala);

                                if (hasLabel)
                                {
                                    // The label is muted, the way a widget's caption is: it is
                                    // there to be read second. The iOS lock screen date is
                                    // dimmer than the clock and set in a wider face.
                                    Color label = Color.FromArgb(inkAlpha * 72 / 100, ink);
                                    DrawShadowedText(g, lastSubtitle, labelFont, labelRect, format, label,
                                                     inkAlpha, scale * 0.7f, shadowSkala);
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
            /// Menggambar teks dengan bayangan yang sesuai gaya.
            ///
            /// Ada DUA jenis bayangan di sini, dan memilih yang salah merusak
            /// tampilannya:
            ///
            ///   halo  - huruf digambar delapan kali mengelilingi titik pusat,
            ///           lalu huruf aslinya di atasnya. Ini benar untuk huruf
            ///           TEBAL: bayangannya menyatu menjadi satu bayangan lembut
            ///           dan hurufnya tetap terbaca.
            ///
            ///   rapat - huruf digambar SEKALI, digeser sedikit ke bawah, lalu
            ///           huruf aslinya di atasnya. Ini yang benar untuk huruf
            ///           TIPIS.
            ///
            /// Kenapa halo tidak boleh dipakai pada huruf tipis: goresan huruf
            /// tipis hanya beberapa piksel, sedangkan halo delapan arah menutupi
            /// area yang jauh lebih luas daripada goresannya sendiri. Mata lalu
            /// membaca BAYANGANNYA sebagai bentuk huruf, dan huruf aslinya
            /// sebagai garis di tengahnya - hasilnya jam terlihat BERONGGA,
            /// seperti huruf yang hanya digambar tepinya. Itu persis keluhan
            /// "ga kayak bener yg ios": jam layar kunci iOS adalah huruf SOLID,
            /// bukan huruf berongga.
            ///
            /// Karena itu gaya tipis memakai `skala = 0`, yang berarti bayangan
            /// rapat saja - dan bayangan rapat tidak pernah mengubah bentuk
            /// huruf karena ia hanya satu salinan yang digeser.
            /// </summary>
            private static void DrawShadowedText(Graphics g, string text, Font font, RectangleF rect,
                                                 StringFormat format, Color colour, int alpha, float scale,
                                                 float skala = 1f)
            {
                if (skala <= 0.01f)
                {
                    // Bayangan rapat: satu salinan, digeser ke bawah.
                    //
                    // Bayangan layar kunci iOS hampir tidak terlihat - yang
                    // membuatnya terbaca adalah ketebalan hurufnya. Tetapi pada
                    // wallpaper yang terang, teks putih tanpa bayangan sama
                    // sekali bisa hilang; satu salinan gelap tipis di bawahnya
                    // menjaga keterbacaan tanpa terlihat sebagai efek.
                    float turun = Math.Max(1f, 1.4f * scale);
                    using (var lembut = new SolidBrush(Color.FromArgb(
                        Math.Min(120, Math.Max(30, (int)(64 * scale))), 0, 0, 0)))
                    {
                        var bawah = new RectangleF(rect.X, rect.Y + turun, rect.Width, rect.Height);
                        g.DrawString(text, font, lembut, bawah, format);
                    }

                    using (var brush = new SolidBrush(Color.FromArgb(alpha, colour)))
                    {
                        g.DrawString(text, font, brush, rect, format);
                    }
                    return;
                }

                float radius = Math.Max(0.4f, 1.6f * scale * skala);
                int shadowAlpha = Math.Min(150, Math.Max(18,
                    (int)(90 * Math.Min(1.6f, scale) * skala)));

                using (var shadow = new SolidBrush(Color.FromArgb(shadowAlpha, 0, 0, 0)))
                {
                    int arah = skala >= 0.9f ? 8 : 4;
                    for (int i = 0; i < arah; i++)
                    {
                        double angle = Math.PI * 2 * i / arah;
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
