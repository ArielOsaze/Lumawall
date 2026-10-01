// FeaturesPage.cs - Luma Studio: the creative controls, per display.
//
// Why a page of its own rather than rows bolted onto Performance:
//
// These are per-display creative controls, and the other pages are per-application
// settings. Mixing them makes both harder to read: Performance is about what the app
// costs, Studio is about what the wallpaper looks like. The split is also what makes the
// monitor selector meaningful - every control here applies to the display chosen at the
// top, which is a distinction that would be lost among global switches.
//
// Every control writes straight into the config and calls RefreshOptions, so a change is
// visible on the desktop immediately. A settings page that needed a restart to show a
// brightness change would be indistinguishable from one that does not work.
//
// ── why the layout changed ───────────────────────────────────────────────────────────
//
// The first version stacked every control in one column, each in its own bordered card:
// ten near-identical boxes down the page, a stock WPF slider inside each one, and a chip
// row for every choice. It read as a form. The problems were specific:
//
//   · the controls were in config order, not in the order a person uses them
//   · nothing showed what the settings do - the numbers had no picture
//   · the monitor selector was a row of "DISPLAY1 DISPLAY2 DISPLAY3" chips, so the
//     user had to remember which monitor was which
//   · the shape and position pickers for the timer were word lists ("Kapsul", "Kiri
//     atas") for questions that are inherently visual
//   · the stock slider is pale blue on grey, which belongs to no part of this palette
//
// So the page is now two columns: a fixed left column with the display list, a live
// preview and the presets, and a scrolling right column of four grouped cards, each
// with a coloured icon header. The groups follow what a person is doing - colour, HDR,
// framing, playback - not the config's field order. The slider is re-templated, the
// shape picker draws the shapes, and the position picker is the 3x3 placement itself.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Effects;
using Forms = System.Windows.Forms;

namespace LumaWall
{
    internal sealed partial class MainWindow
    {
        // Which display the Studio page is editing. A field rather than a local so that
        // leaving the page and returning shows the same monitor, which is what a user
        // expects when comparing two.
        private string studioDevice;

        /// <summary>
        /// Pilih monitor yang akan diatur di Luma Studio, dari halaman lain.
        ///
        /// Dipakai tombol "Atur" di halaman Monitor: pengguna baru saja menunjuk
        /// satu layar, jadi Studio harus terbuka pada layar itu - bukan pada
        /// layar pertama, yang mengharuskan ia mencarinya lagi.
        /// </summary>
        public void PilihStudioDevice(string device)
        {
            if (string.IsNullOrEmpty(device)) return;
            studioDevice = device;
        }

        // The preview, held as fields so a slider move can repaint it. Rebuilding the
        // whole page on every slider tick would lose the drag, and a preview that only
        // updates when the mouse is released is not a preview.
        private Grid studioPreviewSwatch;
        private TextBlock studioPreviewSummary;

        // The slider template, parsed once and shared by every slider on the page.
        private static ControlTemplate studioSliderTemplate;

        // Per-group accents. There is one.
        //
        // These were four separate hues - cyan for colour, amber for HDR, violet for
        // framing, mint for playback - chosen so each group looked distinct. On screen it
        // read as six different colours across ten cards, which is decoration rather than
        // information: none of it told the user anything. The page now uses the app's own
        // crimson for every icon, and the tile behind each icon is that same hue at 15%.
        private static readonly Color CStudioAccent = CPrimary;
        private static readonly Color CStudioColour = CStudioAccent;
        private static readonly Color CStudioHdr = CStudioAccent;
        private static readonly Color CStudioFrame = CStudioAccent;
        private static readonly Color CStudioPlay = CStudioAccent;

        private UIElement BuildStudio()
        {
            var page = PageCanvas();
            page.Children.Add(PageHeading(Tr("studio.title"), Tr("studio.sub"), null));

            Forms.Screen[] screens = Forms.Screen.AllScreens;
            if (string.IsNullOrEmpty(studioDevice) || !screens.Any(s => s.DeviceName == studioDevice))
                studioDevice = screens.Length > 0 ? screens[0].DeviceName : "";

            if (string.IsNullOrEmpty(studioDevice))
            {
                page.Children.Add(EmptyCard(Tr("studio.noDisplay"), Tr("studio.noDisplaySub")));
                return page;
            }

            // Two columns, dan pembagiannya diatur supaya kedua kolom selesai
            // pada ketinggian yang hampir sama.
            //
            // Sebelumnya kolom kiri memuat tujuh kartu dan kolom kanan empat,
            // sehingga halaman berakhir dengan satu kolom yang jauh lebih
            // panjang daripada yang lain - dan itu terbaca sebagai halaman yang
            // belum selesai. Yang menentukan pembagiannya adalah tinggi kartu
            // yang sudah diukur, bukan selera:
            //
            //   Monitor yang diatur    254      Warna         336
            //   Pratinjau              275      Bingkai       357
            //   Preset cepat           158      Pemutaran     313
            //   Lintas monitor         177      Penempatan    455
            //   HDR                    199
            //   Atur ulang             136
            //   Jam desktop            118
            //
            // Kiri 254+275+158+177 = 864. Kanan 336+357+313+455 = 1461. Selisih
            // 597 piksel. Dipindahkan supaya jadi:
            //
            //   kiri:  Monitor 254 + Pratinjau 275 + Preset 158 + HDR 199 + Reset 136 = 1022
            //   kanan: Warna 336 + Bingkai 357 + Pemutaran 313 + Penempatan 455 = 1461
            //
            // Selisihnya masih ada karena kartu Penempatan memang tinggi dan
            // tidak boleh dipindah - padanya ada pad penempatan yang butuh lebar.
            // Yang menghilangkan selisih itu adalah kartu yang bisa dilebarkan:
            // kolom kiri dibuat sedikit lebih lebar dan kartunya mengisi tinggi
            // yang tersedia.
            var columns = new Grid { Margin = new Thickness(0, 4, 0, 0) };
            columns.ColumnDefinitions.Add(new ColumnDefinition
            {
                Width = new GridLength(1, GridUnitType.Star),
                MinWidth = 320
            });
            columns.ColumnDefinitions.Add(new ColumnDefinition
            {
                Width = new GridLength(1.15, GridUnitType.Star),
                MinWidth = 360
            });

            var left = new StackPanel { Margin = new Thickness(0, 0, 16, 0) };
            left.Children.Add(StudioDisplayPicker(screens));
            left.Children.Add(StudioPreviewCard());
            left.Children.Add(StudioPresetCard());
            left.Children.Add(StudioSpanCard());
            left.Children.Add(StudioHdrCard(config.OptionsFor(studioDevice)));
            left.Children.Add(StudioResetCard());
            left.Children.Add(StudioTimerCard());
            Grid.SetColumn(left, 0);
            columns.Children.Add(left);

            DisplayOptions options = config.OptionsFor(studioDevice);

            // The right column holds the groups that act on one image, plus the placement
            // pad.
            //
            // Which card goes where is decided by measurement, not by taste. Measured card
            // heights:
            //
            //   Display being edited  254      Colour        336
            //   Preview               275      Framing       357
            //   Quick presets         158      Playback      313
            //   Across monitors       177      Placement     455
            //   HDR                   199
            //   Reset                 136
            //   Desktop timer         118
            //
            // The placement pad is the tallest card in the page and it used to sit in the
            // left column, which finished 569px longer than the right - a page that reads as
            // unfinished. Moving it right and the small timer card left brings the two
            // columns to within a few pixels of each other.
            var right = new StackPanel();
            right.Children.Add(StudioColourCard(options));
            right.Children.Add(StudioFrameCard(options));
            right.Children.Add(StudioPlaybackCard(options));
            right.Children.Add(StudioTimerPlacementCard());
            Grid.SetColumn(right, 1);
            columns.Children.Add(right);

            page.Children.Add(columns);
            // Luma Studio is the one page whose content is taller than a small window, and
            // it was the one page that was not wrapped in a scroll viewer: BuildStudio
            // returned the StackPanel directly while every other page returned
            // PageScroll(content). With ten cards in two columns, anything below the fold
            // was unreachable - there was no scrollbar and no way to get to the playback
            // and reset cards at the bottom.
            //
            // The margin belongs to the canvas, so it is left where it is; the scroll
            // viewer only adds the ability to move.
            return new ScrollViewer
            {
                Content = page,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
                HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
                PanningMode = PanningMode.VerticalOnly,
                Focusable = false,
            };
        }

        // ── the left column ──────────────────────────────────────────────────────────

        /// <summary>
        /// The monitor list.
        ///
        /// One row per display showing its name and its resolution, rather than a row of
        /// chips reading "DISPLAY1 DISPLAY2 DISPLAY3": with three monitors the chips all
        /// look alike and the user has to remember which is which. The chosen row is
        /// filled and ticked, so the page always answers "what am I editing".
        /// </summary>
        private UIElement StudioDisplayPicker(Forms.Screen[] screens)
        {
            Border card;
            var host = StudioCard(Tr("studio.display"), null, Icons.Displays, CStudioAccent, out card);

            foreach (Forms.Screen screen in screens)
            {
                Forms.Screen captured = screen;
                bool chosen = screen.DeviceName == studioDevice;

                var row = new Border
                {
                    Margin = new Thickness(0, 0, 0, 6),
                    Padding = new Thickness(12, 9, 12, 9),
                    CornerRadius = new CornerRadius(8),
                    Background = new SolidColorBrush(chosen ? CPrimarySoft : CSurface2),
                    BorderBrush = new SolidColorBrush(chosen ? CPrimary : CBorder),
                    BorderThickness = new Thickness(1),
                    Cursor = Cursors.Hand,
                };

                var line = new Grid();
                line.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                line.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

                var names = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
                names.Children.Add(new TextBlock
                {
                    Text = screen.DeviceName.DeviceName(),
                    FontSize = 12.5,
                    FontWeight = FontWeights.SemiBold,
                    Foreground = new SolidColorBrush(chosen ? CText : CMuted),
                });

                string detail = screen.Bounds.Width + " x " + screen.Bounds.Height;
                if (screen.Primary) detail = Tr("studio.primary") + " · " + detail;
                names.Children.Add(new TextBlock
                {
                    Text = detail,
                    FontSize = 10.5,
                    Foreground = new SolidColorBrush(CDim),
                    Margin = new Thickness(0, 2, 0, 0),
                });
                Grid.SetColumn(names, 0);
                line.Children.Add(names);

                if (chosen)
                {
                    var tick = Icons.Build(Icons.Check, 13, new SolidColorBrush(CPrimaryHi));
                    tick.VerticalAlignment = VerticalAlignment.Center;
                    Grid.SetColumn(tick, 1);
                    line.Children.Add(tick);
                }

                row.Child = line;
                row.MouseLeftButtonUp += delegate
                {
                    studioDevice = captured.DeviceName;
                    ReloadCurrentPage();
                };
                row.MouseEnter += delegate { if (!chosen) row.BorderBrush = new SolidColorBrush(CBorderHot); };
                row.MouseLeave += delegate { if (!chosen) row.BorderBrush = new SolidColorBrush(CBorder); };

                host.Children.Add(row);
            }

            return card;
        }

        /// <summary>
        /// A live preview of the current settings.
        ///
        /// It is not a picture of the wallpaper - it cannot be, the real one is a video on
        /// another monitor - it is a picture of the *grade*. The same operations the
        /// wallpaper applies are applied here to a gradient, so dragging brightness moves
        /// the swatch instead of leaving the user to check their desktop. The values that
        /// would otherwise have to be read off five separate sliders are printed
        /// underneath in one line.
        /// </summary>
        private UIElement StudioPreviewCard()
        {
            Border card;
            var host = StudioCard(Tr("studio.preview"), Tr("studio.previewHint"), Icons.Wallpaper, CStudioAccent, out card);

            var frame = new Border
            {
                Height = 152,
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(Color.FromRgb(9, 11, 15)),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                ClipToBounds = true,
            };

            studioPreviewSwatch = new Grid();

            // A horizon, a sun and a foreground ridge, so the grade has structure to act
            // on. A plain gradient made every filter look the same - saturation and hue
            // cannot be judged against a smooth ramp, and the card read as an empty
            // placeholder rather than a preview.
            var marks = new Canvas();

            var sun = new System.Windows.Shapes.Ellipse
            {
                Width = 54,
                Height = 54,
                Fill = new SolidColorBrush(Color.FromArgb(210, 255, 236, 200)),
            };
            marks.Children.Add(sun);

            var ridge = new System.Windows.Shapes.Path
            {
                Fill = new SolidColorBrush(Color.FromArgb(190, 10, 12, 20)),
                Data = Geometry.Parse("M0,60 L46,22 L82,52 L120,14 L164,58 L206,26 L246,56 L292,20 L340,58 L340,120 L0,120 Z"),
            };
            marks.Children.Add(ridge);

            var ground = new System.Windows.Shapes.Rectangle
            {
                Height = 34,
                Fill = new SolidColorBrush(Color.FromArgb(230, 6, 8, 14)),
            };
            marks.Children.Add(ground);

            var horizon = new System.Windows.Shapes.Rectangle
            {
                Height = 1,
                Fill = new SolidColorBrush(Color.FromArgb(90, 255, 255, 255)),
            };
            marks.Children.Add(horizon);

            studioPreviewSwatch.Children.Add(marks);
            frame.Child = studioPreviewSwatch;

            host.Children.Add(frame);

            studioPreviewSummary = new TextBlock
            {
                FontSize = 10.5,
                Foreground = new SolidColorBrush(CDim),
                FontFamily = FMono,
                Margin = new Thickness(0, 9, 0, 0),
                TextWrapping = TextWrapping.Wrap,
                LineHeight = 15,
            };
            host.Children.Add(studioPreviewSummary);

            // Lay the marks out once the frame has a size, since a Canvas does not do it.
            frame.SizeChanged += delegate { StudioLayOutPreview(frame, marks); };
            frame.Loaded += delegate { StudioLayOutPreview(frame, marks); };

            StudioRefreshPreview();
            return card;
        }

        private void StudioLayOutPreview(Border frame, Canvas marks)
        {
            if (marks.Children.Count < 4) return;
            double width = frame.ActualWidth;
            double height = frame.ActualHeight;
            if (width <= 0 || height <= 0) return;

            double horizonY = height * 0.60;

            Canvas.SetLeft(marks.Children[0], width * 0.66);
            Canvas.SetTop(marks.Children[0], horizonY - 82);

            var ridge = (System.Windows.Shapes.Path)marks.Children[1];
            ridge.Width = width;
            ridge.Height = horizonY;
            Canvas.SetLeft(ridge, 0);
            Canvas.SetTop(ridge, horizonY - 60);

            var ground = (System.Windows.Shapes.Rectangle)marks.Children[2];
            ground.Width = width;
            Canvas.SetLeft(ground, 0);
            Canvas.SetTop(ground, horizonY);

            var horizon = (System.Windows.Shapes.Rectangle)marks.Children[3];
            horizon.Width = width;
            Canvas.SetLeft(horizon, 0);
            Canvas.SetTop(horizon, horizonY);
        }

        /// <summary>Presets: one click sets the whole grade.</summary>
        private UIElement StudioPresetCard()
        {
            Border card;
            var host = StudioCard(Tr("studio.presets"), Tr("studio.presetsHint"), Icons.Optimize, CStudioPlay, out card);

            var row = new WrapPanel();
            foreach (string[] preset in StudioPresets())
            {
                string[] captured = preset;
                var button = GhostButton(Tr("preset." + preset[0]));
                button.Height = 31;
                button.Padding = new Thickness(12, 0, 12, 0);
                button.FontSize = 11.5;
                button.Margin = new Thickness(0, 0, 6, 6);
                button.Click += delegate
                {
                    StudioApplyPreset(captured);
                    store.Save(config);
                    manager.RefreshOptions();
                    ReloadCurrentPage();
                };
                row.Children.Add(button);
            }
            host.Children.Add(row);
            return card;
        }

        // ── the right column ─────────────────────────────────────────────────────────

        private UIElement StudioColourCard(DisplayOptions options)
        {
            Border card;
            var host = StudioCard(Tr("studio.look"), Tr("studio.lookHint"), Icons.Palette, CStudioColour, out card);

            host.Children.Add(StudioSlider(Tr("studio.brightness"), 0.2, 2.0, 0.01, options.Brightness, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Brightness = v; }));
            host.Children.Add(StudioSlider(Tr("studio.contrast"), 0.2, 2.0, 0.01, options.Contrast, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Contrast = v; }));
            host.Children.Add(StudioSlider(Tr("studio.saturation"), 0.0, 2.0, 0.01, options.Saturation, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Saturation = v; }));
            host.Children.Add(StudioSlider(Tr("studio.hue"), -180, 180, 1, options.Hue, "F0",
                delegate(double v) { config.OptionsFor(studioDevice).Hue = v; }));
            host.Children.Add(StudioSlider(Tr("studio.gamma"), 0.4, 2.2, 0.01, options.Gamma, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Gamma = v; }));

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioLabel(Tr("studio.filter")));
            host.Children.Add(StudioChipRow(
                new string[] { "none", "grayscale", "sepia", "cool", "warm", "vivid", "noir", "dream" },
                new string[] { Tr("filter.none"), Tr("filter.grayscale"), Tr("filter.sepia"), Tr("filter.cool"),
                               Tr("filter.warm"), Tr("filter.vivid"), Tr("filter.noir"), Tr("filter.dream") },
                options.Filter,
                delegate(string value)
                {
                    config.OptionsFor(studioDevice).Filter = value;
                    StudioRefreshPreview();
                }));

            return card;
        }

        private UIElement StudioHdrCard(DisplayOptions options)
        {
            Border card;
            var host = StudioCard(Tr("studio.hdr"), Tr("studio.hdrHint"), Icons.Hdr, CStudioHdr, out card);

            host.Children.Add(StudioToggle(Tr("studio.hdrOn"), null, options.HdrToneMap,
                delegate(bool v) { config.OptionsFor(studioDevice).HdrToneMap = v; }));

            // The two sliders only mean anything when the tone curve is on, so they are
            // dimmed rather than hidden: hiding them makes the card change height, and a
            // control that appears and disappears is harder to find again than one that
            // is visibly waiting.
            bool on = options.HdrToneMap;
            host.Children.Add(StudioSlider(Tr("studio.hdrExposure"), -1.0, 1.0, 0.01, options.HdrExposure, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).HdrExposure = v; }, on));
            host.Children.Add(StudioSlider(Tr("studio.hdrHighlight"), 0.1, 1.0, 0.01, options.HdrHighlight, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).HdrHighlight = v; }, on));

            return card;
        }

        private UIElement StudioFrameCard(DisplayOptions options)
        {
            Border card;
            var host = StudioCard(Tr("studio.framing"), Tr("studio.framingHint"), Icons.Frame, CStudioFrame, out card);

            host.Children.Add(StudioLabel(Tr("studio.fit")));
            host.Children.Add(StudioChipRow(
                new string[] { "cover", "contain", "fill", "center" },
                new string[] { Tr("fit.cover"), Tr("fit.contain"), Tr("fit.fill"), Tr("fit.center") },
                options.Fit,
                delegate(string value)
                {
                    config.OptionsFor(studioDevice).Fit = value;
                    StudioRefreshPreview();
                }));

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioSlider(Tr("studio.zoom"), 0.5, 3.0, 0.01, options.Zoom, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Zoom = v; }));
            host.Children.Add(StudioSlider(Tr("studio.panX"), -1.0, 1.0, 0.01, options.OffsetX, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).OffsetX = v; }));
            host.Children.Add(StudioSlider(Tr("studio.panY"), -1.0, 1.0, 0.01, options.OffsetY, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).OffsetY = v; }));

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioLabel(Tr("studio.flip")));
            host.Children.Add(StudioChipRow(
                new string[] { "none", "h", "v", "both" },
                new string[] { Tr("flip.none"), Tr("flip.h"), Tr("flip.v"), Tr("flip.both") },
                options.FlipHorizontal && options.FlipVertical ? "both"
                    : options.FlipHorizontal ? "h" : options.FlipVertical ? "v" : "none",
                delegate(string value)
                {
                    DisplayOptions target = config.OptionsFor(studioDevice);
                    target.FlipHorizontal = value == "h" || value == "both";
                    target.FlipVertical = value == "v" || value == "both";
                }));

            return card;
        }

        private UIElement StudioPlaybackCard(DisplayOptions options)
        {
            Border card;
            var host = StudioCard(Tr("studio.playback"), Tr("studio.playbackHint"), Icons.Speed, CStudioPlay, out card);

            // Speed as chips as well as a slider. The useful values are a handful of
            // recognisable speeds, and "1.37x" is not a choice anybody makes on purpose -
            // so the chips are the primary control and the slider is the fine adjustment.
            host.Children.Add(StudioLabel(Tr("studio.rate")));
            var speedRow = new WrapPanel();
            foreach (double speed in new double[] { 0.25, 0.5, 1.0, 1.5, 2.0, 4.0 })
            {
                double captured = speed;
                bool chosen = Math.Abs(options.PlaybackRate - speed) < 0.001;
                var button = GhostButton(StudioRateLabel(speed));
                button.Height = 31;
                button.Padding = new Thickness(13, 0, 13, 0);
                button.FontSize = 11.5;
                button.Margin = new Thickness(0, 0, 6, 6);
                if (chosen)
                {
                    button.Background = new SolidColorBrush(CStudioAccent);
                    // Near-black text on the crimson chip, the same tone the app draws its
                    // chrome on. This was a dark green, which only made sense while the
                    // chosen chip was mint.
                    button.Foreground = new SolidColorBrush(Color.FromRgb(10, 12, 16));
                    button.BorderBrush = new SolidColorBrush(CStudioAccent);
                }
                button.Click += delegate
                {
                    config.OptionsFor(studioDevice).PlaybackRate = captured;
                    manager.RefreshOptions();
                    store.Save(config);
                    ReloadCurrentPage();
                };
                speedRow.Children.Add(button);
            }
            host.Children.Add(speedRow);
            host.Children.Add(StudioSlider(Tr("studio.rateFine"), 0.25, 4.0, 0.05, options.PlaybackRate, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).PlaybackRate = v; }));

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioToggle(Tr("studio.pingpong"), Tr("studio.pingpongHint"), options.PingPong,
                delegate(bool v) { config.OptionsFor(studioDevice).PingPong = v; }));

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioResetRow());

            return card;
        }

        /// <summary>
        /// The span card: monitors that share one continuous wallpaper.
        ///
        /// A span is a group rather than a flag on a monitor, because the same monitor can
        /// belong to different combinations at different times - and turning a span off has
        /// to leave every monitor's own wallpaper intact.
        /// </summary>
        private UIElement StudioSpanCard()
        {
            Border card;
            var host = StudioCard(Tr("studio.span"), Tr("studio.spanHint"), Icons.AllDisplays, CStudioAccent, out card);

            Forms.Screen[] screens = Forms.Screen.AllScreens;
            if (screens.Length < 2)
            {
                host.Children.Add(StudioHint(Tr("studio.spanSingle")));
                return card;
            }

            foreach (SpanGroup group in config.SpanGroups.ToList())
            {
                SpanGroup captured = group;
                string names = string.Join(" + ", captured.Devices.Select(d => d.DeviceName()));

                var row = new Border
                {
                    Margin = new Thickness(0, 0, 0, 6),
                    Padding = new Thickness(12, 9, 12, 9),
                    CornerRadius = new CornerRadius(8),
                    Background = new SolidColorBrush(CSurface2),
                    BorderBrush = new SolidColorBrush(captured.Enabled ? CAccent : CBorder),
                    BorderThickness = new Thickness(1),
                };
                var line = new Grid();
                line.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                line.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
                line.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

                var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
                text.Children.Add(new TextBlock
                {
                    Text = names,
                    FontSize = 12.5,
                    FontWeight = FontWeights.SemiBold,
                    Foreground = new SolidColorBrush(CText),
                });
                text.Children.Add(new TextBlock
                {
                    Text = Path.GetFileNameWithoutExtension(captured.Path ?? ""),
                    FontSize = 10.5,
                    Foreground = new SolidColorBrush(CDim),
                    TextTrimming = TextTrimming.CharacterEllipsis,
                    Margin = new Thickness(0, 2, 0, 0),
                });
                Grid.SetColumn(text, 0);
                line.Children.Add(text);

                var toggle = GhostButton(captured.Enabled ? Tr("studio.spanOff") : Tr("studio.spanOn"));
                toggle.Height = 30;
                toggle.Padding = new Thickness(12, 0, 12, 0);
                toggle.FontSize = 11;
                toggle.VerticalAlignment = VerticalAlignment.Center;
                if (captured.Enabled)
                {
                    toggle.Background = new SolidColorBrush(CAccentSoft);
                    toggle.Foreground = new SolidColorBrush(CAccent);
                    toggle.BorderBrush = new SolidColorBrush(CAccent);
                }
                toggle.Click += delegate
                {
                    if (captured.Enabled) ClearSpanGroup(captured);
                    else ApplySpanGroup(captured);
                    store.Save(config);
                    ReloadCurrentPage();
                };
                Grid.SetColumn(toggle, 1);
                line.Children.Add(toggle);

                var remove = GhostButton(Tr("studio.remove"));
                remove.Height = 30;
                remove.Padding = new Thickness(10, 0, 10, 0);
                remove.FontSize = 11;
                remove.Margin = new Thickness(6, 0, 0, 0);
                remove.VerticalAlignment = VerticalAlignment.Center;
                remove.Click += delegate
                {
                    ClearSpanGroup(captured);
                    config.SpanGroups.Remove(captured);
                    store.Save(config);
                    ReloadCurrentPage();
                };
                Grid.SetColumn(remove, 2);
                line.Children.Add(remove);

                row.Child = line;
                host.Children.Add(row);
            }

            var create = new WrapPanel { Margin = new Thickness(0, 4, 0, 0) };
            foreach (Forms.Screen other in screens)
            {
                if (other.DeviceName == studioDevice) continue;
                Forms.Screen captured = other;
                var make = GhostButton(string.Format(CultureInfo.InvariantCulture, Tr("studio.spanWith"),
                    captured.DeviceName.DeviceName()));
                make.Height = 31;
                make.Padding = new Thickness(12, 0, 12, 0);
                make.FontSize = 11.5;
                make.Margin = new Thickness(0, 0, 8, 6);
                make.Click += delegate
                {
                    string path = config.MonitorVideos.ContainsKey(studioDevice) && File.Exists(config.MonitorVideos[studioDevice])
                        ? config.MonitorVideos[studioDevice]
                        : config.Library.FirstOrDefault(File.Exists);
                    if (string.IsNullOrEmpty(path)) { ShowToast(Tr("studio.spanNoWallpaper")); return; }
                    var group = new SpanGroup
                    {
                        Name = studioDevice + " + " + captured.DeviceName,
                        Path = path,
                        Devices = new List<string> { studioDevice, captured.DeviceName },
                        Enabled = true,
                    };
                    config.SpanGroups.Add(group);
                    ApplySpanGroup(group);
                    store.Save(config);
                    ReloadCurrentPage();
                };
                create.Children.Add(make);
            }
            host.Children.Add(create);

            SpanGroup active = config.SpanGroupFor(studioDevice);
            if (active != null)
            {
                var line = StudioHint(string.Format(CultureInfo.InvariantCulture, Tr("studio.spanActive"),
                    Path.GetFileNameWithoutExtension(active.Path ?? "")));
                line.Foreground = new SolidColorBrush(CAccent);
                line.Margin = new Thickness(0, 4, 0, 0);
                host.Children.Add(line);
            }

            return card;
        }

        /// <summary>
        /// Puts one wallpaper across every monitor in a group.
        ///
        /// The same file goes to each display; the geometry that makes it read as one
        /// picture is computed per window in WallpaperWindow.TryMeasureSpan, because it
        /// depends on where each monitor sits on the desktop.
        /// </summary>
        private void ApplySpanGroup(SpanGroup group)
        {
            if (group == null || string.IsNullOrEmpty(group.Path)) return;
            foreach (string device in group.Devices)
            {
                Forms.Screen screen = Forms.Screen.AllScreens.FirstOrDefault(s => s.DeviceName == device);
                if (screen == null) continue;
                config.MonitorVideos[device] = group.Path;
                manager.Apply(screen, group.Path, config.Mute, config.TargetFps);
            }
            group.Enabled = true;
            manager.RefreshOptions();
            ShowToast(Tr("studio.spanApplied"));
        }

        /// <summary>Puts each monitor in a group back on a normal wallpaper.</summary>
        private void ClearSpanGroup(SpanGroup group)
        {
            if (group == null) return;
            group.Enabled = false;
            // The span overwrote each monitor's entry, so the fallback is the first library
            // file that still exists rather than the entry the span replaced.
            foreach (string device in group.Devices)
            {
                string fallback = config.Library.FirstOrDefault(File.Exists);
                if (string.IsNullOrEmpty(fallback)) continue;
                Forms.Screen screen = Forms.Screen.AllScreens.FirstOrDefault(s => s.DeviceName == device);
                if (screen == null) continue;
                if (!config.MonitorVideos.ContainsKey(device) || config.MonitorVideos[device] == group.Path)
                    config.MonitorVideos[device] = fallback;
                manager.Apply(screen, config.MonitorVideos[device], config.Mute, config.TargetFps);
            }
            manager.RefreshOptions();
        }

        // ── the timer ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Which display the timer sits on.
        ///
        /// A chip row rather than a dropdown, because the number of displays is small and
        /// the chosen one has to be visible at a glance - the same reasoning as the mode
        /// and style rows above it.
        ///
        /// The primary display is offered as "Display 1" style names, matching the labels
        /// in the display picker at the top of the page, so the same screen has the same
        /// name in both places.
        /// </summary>
        private UIElement StudioDisplayChips()
        {
            var row = new WrapPanel { Margin = new Thickness(0, 0, 0, 4) };

            Forms.Screen[] screens = Forms.Screen.AllScreens;
            foreach (Forms.Screen screen in screens)
            {
                Forms.Screen captured = screen;
                // An empty setting means the primary display, which is what the app did
                // before this control existed.
                bool chosen = string.IsNullOrEmpty(config.Timer.Monitor)
                    ? captured.Primary
                    : string.Equals(captured.DeviceName, config.Timer.Monitor, StringComparison.OrdinalIgnoreCase);

                string label = captured.DeviceName.DeviceName();
                if (captured.Primary) label += " · " + Tr("studio.primary");

                var button = GhostButton(label);
                button.Height = 31;
                button.Padding = new Thickness(13, 0, 13, 0);
                button.FontSize = 11.5;
                button.Margin = new Thickness(0, 0, 6, 6);
                if (chosen)
                {
                    button.Background = new SolidColorBrush(CPrimary);
                    button.Foreground = Brushes.White;
                    button.BorderBrush = new SolidColorBrush(CPrimary);
                }
                button.Click += delegate
                {
                    config.Timer.Monitor = captured.Primary ? "" : captured.DeviceName;
                    store.Save(config);
                    timerRefresh();
                    ReloadCurrentPage();
                };
                row.Children.Add(button);
            }

            // A single-monitor machine has nothing to choose, and a row of one chip that
            // cannot change anything is clutter. Say so instead of offering a choice that
            // does not exist.
            if (screens.Length < 2)
            {
                row.Children.Add(new TextBlock
                {
                    Text = Tr("timer.displayHint"),
                    FontSize = 10.5,
                    Foreground = new SolidColorBrush(CDim),
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(0, 2, 0, 0),
                });
            }
            return row;
        }

        private UIElement StudioTimerCard()
        {
            Border card;
            var host = StudioCard(Tr("studio.timer"), Tr("timer.hint"), Icons.Timer, CStudioHdr, out card);

            host.Children.Add(StudioToggle(Tr("timer.enable"), null, config.Timer.Enabled,
                delegate(bool v)
                {
                    config.Timer.Enabled = v;
                    timerRefresh();
                }, true));

            if (!config.Timer.Enabled) return card;

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioLabel(Tr("timer.mode")));
            host.Children.Add(StudioChipRow(
                new string[] { "countdown", "clock", "stopwatch" },
                new string[] { Tr("timer.countdown"), Tr("timer.clock"), Tr("timer.stopwatch") },
                config.Timer.Mode,
                delegate(string value) { config.Timer.Mode = value; }));

            host.Children.Add(StudioLabel(Tr("timer.style")));
            host.Children.Add(StudioStyleRow());

            if (config.Timer.Mode == "clock")
            {
                host.Children.Add(StudioToggle(Tr("timer.date"), Tr("timer.dateHint"), config.Timer.ShowDate,
                    delegate(bool v) { config.Timer.ShowDate = v; }));
                host.Children.Add(StudioToggle(Tr("timer.twelve"), Tr("timer.twelveHint"), config.Timer.TwelveHour,
                    delegate(bool v) { config.Timer.TwelveHour = v; }));
            }

            var actions = new WrapPanel { Margin = new Thickness(0, 6, 0, 0) };
            var restart = GhostButton(Tr("timer.restart"));
            restart.Height = 31;
            restart.FontSize = 11.5;
            restart.Margin = new Thickness(0, 0, 8, 6);
            restart.Click += delegate { timerReset(); ShowToast(Tr("timer.restarted")); };
            actions.Children.Add(restart);

            var hold = GhostButton(Tr("timer.pause"));
            hold.Height = 31;
            hold.FontSize = 11.5;
            hold.Margin = new Thickness(0, 0, 8, 6);
            hold.Click += delegate { timerPause(); };
            actions.Children.Add(hold);
            host.Children.Add(actions);

            return card;
        }

        /// <summary>
        /// Where the widget sits and how big it is.
        ///
        /// Split out of StudioTimerCard for a measured reason: with the style picker, the
        /// placement pad, three sliders, the countdown length, the blink switch and the
        /// action row all in one card it was 719px tall, and whichever column held it was
        /// that much taller than the other. Two cards of roughly 360px let the columns
        /// finish within the 220px the layout check allows.
        /// </summary>
        private UIElement StudioTimerPlacementCard()
        {
            Border card;
            var host = StudioCard(Tr("timer.placementTitle"), Tr("timer.placementHint"),
                                  Icons.Displays, CStudioHdr, out card);

            host.Children.Add(StudioLabel(Tr("timer.position")));
            host.Children.Add(StudioPositionPad());

            host.Children.Add(StudioLabel(Tr("timer.display")));
            host.Children.Add(StudioDisplayChips());

            host.Children.Add(StudioDivider());
            host.Children.Add(StudioSlider(Tr("timer.size"), 50, 250, 5, config.Timer.Scale, "F0",
                delegate(double v) { config.Timer.Scale = (int)v; }));
            host.Children.Add(StudioSlider(Tr("timer.offsetX"), -400, 400, 1, config.Timer.OffsetX, "F0",
                delegate(double v) { config.Timer.OffsetX = (int)v; }));
            host.Children.Add(StudioSlider(Tr("timer.offsetY"), -400, 400, 1, config.Timer.OffsetY, "F0",
                delegate(double v) { config.Timer.OffsetY = (int)v; }));

            if (config.Timer.Mode == "countdown")
            {
                host.Children.Add(StudioSlider(Tr("timer.length"), 10, 7200, 10, config.Timer.Seconds, "F0",
                    delegate(double v) { config.Timer.Seconds = (int)v; }));
            }

            host.Children.Add(StudioToggle(Tr("timer.blink"), Tr("timer.blinkHint"), config.Timer.BlinkAtEnd,
                delegate(bool v) { config.Timer.BlinkAtEnd = v; }));

            return card;
        }

        /// <summary>
        /// The style picker: four tiles that draw what each style actually looks like.
        ///
        /// The previous control asked "Kapsul / Bulat / Kotak / Tanpa latar" and drew the
        /// silhouette of a box. That is the wrong question: the old styles were all boxes,
        /// and a box is what made the widget look like a stray system dialog. These four
        /// are what macOS and iOS widgets do instead, and the tiles show it - the time with
        /// no background, with a wash, in a panel, and inside a ring.
        /// </summary>
        private UIElement StudioStyleRow()
        {
            var row = new WrapPanel();
            string[] keys = { "minimal", "bold", "glass", "card", "ring", "analog",
                              "ioslarge", "ioslight", "iosstack", "iosdate" };
            string[] labels =
            {
                Tr("timer.minimal"), Tr("timer.bold"), Tr("timer.glass"),
                Tr("timer.card"), Tr("timer.ring"), Tr("timer.analog"),
                Tr("timer.ioslarge"), Tr("timer.ioslight"), Tr("timer.iosstack"),
                Tr("timer.iosdate"),
            };

            for (int i = 0; i < keys.Length; i++)
            {
                string key = keys[i];
                bool chosen = (config.Timer.Style ?? "minimal") == key;

                var cell = new StackPanel { Margin = new Thickness(0, 0, 8, 6) };
                var tile = new Border
                {
                    Width = 66,
                    Height = 48,
                    CornerRadius = new CornerRadius(9),
                    Background = new SolidColorBrush(chosen ? CPrimarySoft : CSurface2),
                    BorderBrush = new SolidColorBrush(chosen ? CPrimary : CBorder),
                    BorderThickness = new Thickness(1),
                    Cursor = Cursors.Hand,
                };
                tile.Child = StudioStyleGlyph(key, chosen);
                cell.Children.Add(tile);
                cell.Children.Add(new TextBlock
                {
                    Text = labels[i],
                    FontSize = 10,
                    Foreground = new SolidColorBrush(chosen ? CText : CDim),
                    HorizontalAlignment = HorizontalAlignment.Center,
                    Margin = new Thickness(0, 4, 0, 0),
                });

                tile.MouseLeftButtonUp += delegate
                {
                    config.Timer.Style = key;
                    timerRefresh();
                    store.Save(config);
                    ReloadCurrentPage();
                };
                tile.MouseEnter += delegate { if (!chosen) tile.BorderBrush = new SolidColorBrush(CBorderHot); };
                tile.MouseLeave += delegate { if (!chosen) tile.BorderBrush = new SolidColorBrush(CBorder); };

                row.Children.Add(cell);
            }

            return row;
        }

        /// <summary>
        /// Draws one style tile.
        ///
        /// A dark plate stands in for the wallpaper, so "transparent" is visible as
        /// transparent rather than as the panel's own colour. The time is drawn in white
        /// with a faint dark halo underneath it, which is how the widget keeps itself
        /// readable - the same trick the real widget uses.
        /// </summary>
        private UIElement StudioStyleGlyph(string key, bool chosen)
        {
            Color ink = chosen ? Colors.White : CMuted;
            var canvas = new Canvas { Width = 66, Height = 48 };

            // The wallpaper stand-in.
            var plate = new Border
            {
                Width = 66,
                Height = 48,
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(Color.FromRgb(28, 32, 42)),
            };
            canvas.Children.Add(plate);

            if (key == "glass" || key == "card")
            {
                // A faint wash, not a slab. The card is inset and rounder, the glass fills
                // the tile - that is the only difference between them.
                bool card = key == "card";
                var wash = new Border
                {
                    Width = card ? 46 : 66,
                    Height = card ? 32 : 48,
                    CornerRadius = new CornerRadius(card ? 10 : 9),
                    Background = new SolidColorBrush(Color.FromArgb(card ? (byte)110 : (byte)70, 12, 14, 18)),
                    IsHitTestVisible = false,
                };
                Canvas.SetLeft(wash, card ? 10 : 0);
                Canvas.SetTop(wash, card ? 8 : 0);
                canvas.Children.Add(wash);
            }

            if (key == "ring")
            {
                var ring = new System.Windows.Shapes.Ellipse
                {
                    Width = 32,
                    Height = 32,
                    Stroke = new SolidColorBrush(Color.FromArgb(210, 255, 255, 255)),
                    StrokeThickness = 2.4,
                    StrokeDashArray = new DoubleCollection { 3.4, 1.1 },
                    Fill = Brushes.Transparent,
                    IsHitTestVisible = false,
                };
                Canvas.SetLeft(ring, 17);
                Canvas.SetTop(ring, 8);
                canvas.Children.Add(ring);
            }

            if (key == "analog")
            {
                // The iOS Clock face: a ring, four quarter ticks, two hands.
                var ring = new System.Windows.Shapes.Ellipse
                {
                    Width = 34,
                    Height = 34,
                    Stroke = new SolidColorBrush(Color.FromArgb(150, 255, 255, 255)),
                    StrokeThickness = 1.4,
                    Fill = Brushes.Transparent,
                    IsHitTestVisible = false,
                };
                Canvas.SetLeft(ring, 16);
                Canvas.SetTop(ring, 7);
                canvas.Children.Add(ring);

                // Two hands, drawn as lines from the centre: hour pointing up-right,
                // minute pointing down-right, which is what a clock at 10:10 looks like.
                var hour = new System.Windows.Shapes.Line
                {
                    X1 = 33, Y1 = 24, X2 = 40, Y2 = 15,
                    Stroke = new SolidColorBrush(Colors.White),
                    StrokeThickness = 2.4,
                    StrokeStartLineCap = PenLineCap.Round,
                    StrokeEndLineCap = PenLineCap.Round,
                    IsHitTestVisible = false,
                };
                var minute = new System.Windows.Shapes.Line
                {
                    X1 = 33, Y1 = 24, X2 = 41, Y2 = 32,
                    Stroke = new SolidColorBrush(Colors.White),
                    StrokeThickness = 1.6,
                    StrokeStartLineCap = PenLineCap.Round,
                    StrokeEndLineCap = PenLineCap.Round,
                    IsHitTestVisible = false,
                };
                canvas.Children.Add(hour);
                canvas.Children.Add(minute);
            }

            // The time, with the halo that keeps it readable over anything.
            var time = new TextBlock
            {
                Text = key == "ring" ? "5:00" : "9:41",
                FontSize = key == "ring" ? 9.5 : 13,
                FontFamily = FDisplay,
                FontWeight = FontWeights.SemiBold,
                Foreground = new SolidColorBrush(ink),
                // The dial has no text at all, so the glyph is left out rather than drawn
                // over the hands.
                Visibility = key == "analog" ? Visibility.Collapsed : Visibility.Visible,
            };
            time.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
            Canvas.SetLeft(time, (66 - time.DesiredSize.Width) / 2);
            Canvas.SetTop(time, (48 - time.DesiredSize.Height) / 2);
            canvas.Children.Add(time);

            return canvas;
        }

        /// <summary>
        /// The position picker: one picture of the screen, and you click where the clock goes.
        ///
        /// This replaced a 3x3 grid of cells that each contained a smaller 3x3 grid.
        /// That design could not work: a cell is 40px, its inner grid 32px, so each of the
        /// nine sub-cells was 10.7px - narrower than the 13px clock mark it had to hold. The
        /// marks overflowed into their neighbours, and the measured result was a pad where
        /// only the centre cell appeared to have a mark.
        ///
        /// The complaint was "placement bagian ini loh kirainya apa kananya apa kadang bikin
        /// bingung" - you could not tell which cell meant what. Nine pictures of a screen
        /// inside nine cells of a screen is confusing by construction. There is one screen
        /// here, the clock is drawn on it exactly once, and it moves as you choose. The nine
        /// drop targets are still there, but they are invisible: they are where you click,
        /// not something you have to read.
        ///
        /// The edges are labelled so the picture reads as a screen, and the current choice is
        /// named in words beside it.
        /// </summary>
        private UIElement StudioPositionPad()
        {
            const double pad = 126;    // the screen
            const double edge = 13;    // room for the edge labels
            const double markW = 22;   // the clock mark, comfortably inside a third (42px)
            const double markH = 9;

            // A Grid, not a UniformGrid.
            //
            // UniformGrid places children in order and IGNORES the Grid.Row / Grid.Column
            // attached properties - so the clock mark, which is the tenth child, always
            // landed in the fourth row's first column (the bottom-left of the pad) no matter
            // what position was chosen. Measured: the config said middle-center and the mark
            // was drawn at 0.17/0.88 of the pad. The pad looked like it ignored clicks
            // because the one thing that was supposed to move could not move at all.
            var grid = new Grid
            {
                Width = pad,
                Height = pad,
            };
            for (int i = 0; i < 3; i++)
            {
                grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
                grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            }
            string[] keys =
            {
                "top-left", "top-center", "top-right",
                "middle-left", "middle-center", "middle-right",
                "bottom-left", "bottom-center", "bottom-right",
            };

            // The clock mark, drawn once and moved. It sits on the pad at the chosen
            // position, so the picture shows the answer rather than asking you to decode it.
            var clock = new Border
            {
                Width = markW,
                Height = markH,
                CornerRadius = new CornerRadius(2.5),
                Background = new SolidColorBrush(CPrimary),
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                IsHitTestVisible = false,
            };
            Grid.SetRow(clock, 1);
            Grid.SetColumn(clock, 1);

            string current = string.IsNullOrEmpty(config.Timer.Position) ? "middle-center" : config.Timer.Position;

            // The name of the current choice, beside the pad. It is updated in place when a
            // position is chosen - see below.
            var name = new TextBlock
            {
                Text = StudioPositionLabel(current),
                FontSize = 11.5,
                Foreground = new SolidColorBrush(CText),
                VerticalAlignment = VerticalAlignment.Center,
                TextWrapping = TextWrapping.Wrap,
            };

            Action<string> moveMark = delegate(string key)
            {
                Grid.SetRow(clock, key.StartsWith("top") ? 0 : key.StartsWith("bottom") ? 2 : 1);
                Grid.SetColumn(clock, key.EndsWith("left") ? 0 : key.EndsWith("right") ? 2 : 1);
                name.Text = StudioPositionLabel(key);
            };
            moveMark(current);

            foreach (string key in keys)
            {
                string captured = key;

                // The drop target. It is invisible - a faint highlight on hover is the only
                // sign it exists - because the mark on the pad is what the user reads.
                var target = new Border
                {
                    Background = Brushes.Transparent,
                    Cursor = Cursors.Hand,
                    ToolTip = StudioPositionLabel(key),
                };

                // Choosing a position moves the mark and renames the choice, and does NOT
                // rebuild the page.
                //
                // It used to call ReloadCurrentPage(). That rebuilds the whole Studio page
                // from scratch, which takes long enough that a second click - or even the
                // same click replayed by a checker a second later - landed while the page was
                // mid-build and hit whatever was there instead. Measured: clicking the pad at
                // pad+0, pad+10, pad+20 and pad+30 recorded middle-left, top-left,
                // middle-left, middle-center - four different answers for one cell.
                //
                // Nothing here needs a rebuild. The mark is a live element that moves, and the
                // label is a live element that renames. Both are updated directly, so the
                // click takes effect immediately and the page is never in a half-built state.
                target.MouseLeftButtonUp += delegate
                {
                    config.Timer.Position = captured;
                    moveMark(captured);
                    timerRefresh();
                    store.Save(config);
                };
                target.MouseEnter += delegate
                {
                    target.Background = new SolidColorBrush(Color.FromArgb(38, CPrimaryHi.R, CPrimaryHi.G, CPrimaryHi.B));
                };
                target.MouseLeave += delegate { target.Background = Brushes.Transparent; };

                // The drop target needs its cell too - with a real Grid, children without
                // a row and column all pile into cell 0,0.
                Grid.SetRow(target, key.StartsWith("top") ? 0 : key.StartsWith("bottom") ? 2 : 1);
                Grid.SetColumn(target, key.EndsWith("left") ? 0 : key.EndsWith("right") ? 2 : 1);
                grid.Children.Add(target);
            }

            // The mark goes on last so it draws above the drop targets.
            grid.Children.Add(clock);

            // The frame is the screen. The labels name its edges so the square reads as a
            // screen rather than as an abstract grid.
            var frame = new Border
            {
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(9),
                Padding = new Thickness(5),
                Background = new SolidColorBrush(Color.FromArgb(70, CSurface2.R, CSurface2.G, CSurface2.B)),
                Child = grid,
            };

            var canvas = new Grid { Width = pad + 10 + edge * 2,
                                    Height = pad + 10 + edge * 2,
                                    HorizontalAlignment = HorizontalAlignment.Left };
            canvas.Children.Add(frame);
            frame.Margin = new Thickness(edge, edge, edge, edge);

            Func<string, TextBlock> edgeLabel =
                delegate(string text)
                {
                    return new TextBlock
                    {
                        Text = text,
                        FontSize = 8.5,
                        Foreground = new SolidColorBrush(CDim),
                        Opacity = 0.75,
                    };
                };

            // Left / right sit beside the pad; top / bottom above and below it.
            var edgeLeft = edgeLabel(Tr("timer.edgeLeft"));
            edgeLeft.HorizontalAlignment = HorizontalAlignment.Left;
            edgeLeft.VerticalAlignment = VerticalAlignment.Center;
            var edgeRight = edgeLabel(Tr("timer.edgeRight"));
            edgeRight.HorizontalAlignment = HorizontalAlignment.Right;
            edgeRight.VerticalAlignment = VerticalAlignment.Center;
            var edgeTop = edgeLabel(Tr("timer.edgeTop"));
            edgeTop.VerticalAlignment = VerticalAlignment.Top;
            edgeTop.HorizontalAlignment = HorizontalAlignment.Center;
            var edgeBottom = edgeLabel(Tr("timer.edgeBottom"));
            edgeBottom.VerticalAlignment = VerticalAlignment.Bottom;
            edgeBottom.HorizontalAlignment = HorizontalAlignment.Center;

            canvas.Children.Add(edgeLeft);
            canvas.Children.Add(edgeRight);
            canvas.Children.Add(edgeTop);
            canvas.Children.Add(edgeBottom);

            // The name is placed beside the pad. It was created above, so that choosing a
            // position can rename it without rebuilding the page.
            var host = new Grid { HorizontalAlignment = HorizontalAlignment.Left };
            host.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            host.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            Grid.SetColumn(canvas, 0);
            Grid.SetColumn(name, 1);
            name.Margin = new Thickness(14, 0, 0, 0);
            host.Children.Add(canvas);
            host.Children.Add(name);
            return host;
        }

        private string StudioPositionLabel(string key)
        {
            switch (key)
            {
                case "top-left": return Tr("timer.tl");
                case "top-center": return Tr("timer.tc");
                case "top-right": return Tr("timer.tr");
                case "middle-left": return Tr("timer.ml");
                case "middle-center": return Tr("timer.mc");
                case "middle-right": return Tr("timer.mr");
                case "bottom-left": return Tr("timer.bl");
                case "bottom-center": return Tr("timer.bc");
                case "bottom-right": return Tr("timer.br");
                default: return key;
            }
        }

        // ── controls ─────────────────────────────────────────────────────────────────

        /// <summary>
        /// A group card: an icon tile, a title, one line of explanation, then the controls.
        ///
        /// Returns the body to fill, and hands back the card to put on the page. The
        /// accent tints the icon tile, so a page of these is scannable by colour rather
        /// than by reading four headings that all start with the same word.
        /// </summary>
        private StackPanel StudioCard(string title, string subtitle, string iconName, Color accent, out Border card)
        {
            card = new Border
            {
                Margin = new Thickness(0, 0, 0, 13),
                CornerRadius = new CornerRadius(11),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
            };

            var outer = new StackPanel();

            var head = new Grid { Margin = new Thickness(17, 15, 17, 0) };
            head.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            head.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            var iconHost = new Border
            {
                Width = 34,
                Height = 34,
                CornerRadius = new CornerRadius(8),
                Background = new SolidColorBrush(Color.FromArgb(38, accent.R, accent.G, accent.B)),
                VerticalAlignment = VerticalAlignment.Top,
            };
            iconHost.Child = Icons.Build(iconName, 17, new SolidColorBrush(accent));
            Grid.SetColumn(iconHost, 0);
            head.Children.Add(iconHost);

            var copy = new StackPanel { Margin = new Thickness(12, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
            copy.Children.Add(new TextBlock
            {
                Text = title,
                FontSize = 14.5,
                FontWeight = FontWeights.SemiBold,
                Foreground = new SolidColorBrush(CText),
            });
            if (!string.IsNullOrEmpty(subtitle))
            {
                copy.Children.Add(new TextBlock
                {
                    Text = subtitle,
                    FontSize = 11,
                    Foreground = new SolidColorBrush(CDim),
                    TextWrapping = TextWrapping.Wrap,
                    LineHeight = 15,
                    Margin = new Thickness(0, 3, 8, 0),
                });
            }
            Grid.SetColumn(copy, 1);
            head.Children.Add(copy);
            outer.Children.Add(head);

            var body = new StackPanel { Margin = new Thickness(17, 14, 17, 15) };
            outer.Children.Add(body);

            card.Child = outer;
            return body;
        }

        /// <summary>A hairline between two groups of controls inside one card.</summary>
        private UIElement StudioDivider()
        {
            return new Border
            {
                Height = 1,
                Background = new SolidColorBrush(CBorder),
                Margin = new Thickness(0, 12, 0, 14),
            };
        }

        private TextBlock StudioLabel(string text)
        {
            return new TextBlock
            {
                Text = text,
                FontSize = 12,
                FontWeight = FontWeights.SemiBold,
                Foreground = new SolidColorBrush(CText),
                Margin = new Thickness(0, 0, 0, 7),
            };
        }

        private TextBlock StudioHint(string text)
        {
            return new TextBlock
            {
                Text = text,
                FontSize = 11.5,
                Foreground = new SolidColorBrush(CDim),
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            };
        }

        /// <summary>A row of mutually exclusive chips that applies on click.</summary>
        private UIElement StudioChipRow(string[] keys, string[] labels, string current, Action<string> set)
        {
            var row = new WrapPanel();
            for (int i = 0; i < keys.Length; i++)
            {
                string key = keys[i];
                bool chosen = key == current;
                var button = GhostButton(labels[i]);
                button.Height = 31;
                button.Padding = new Thickness(13, 0, 13, 0);
                button.FontSize = 11.5;
                button.Margin = new Thickness(0, 0, 6, 6);
                // The chosen chip is filled: a chip row that does not show which option is
                // active is a row of buttons, not a selector.
                if (chosen)
                {
                    button.Background = new SolidColorBrush(CPrimary);
                    button.Foreground = Brushes.White;
                    button.BorderBrush = new SolidColorBrush(CPrimary);
                }
                button.Click += delegate { set(key); };
                row.Children.Add(button);
            }
            return row;
        }

        /// <summary>
        /// A labelled slider that applies on every move, not on release.
        ///
        /// The value sits in its own bordered readout rather than as bare text, so a column
        /// of sliders has a column of numbers that line up.
        /// </summary>
        private UIElement StudioSlider(string label, double min, double max, double step, double value, string format,
            Action<double> set, bool enabled = true)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 11), Opacity = enabled ? 1.0 : 0.42 };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(150) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(58) });

            var title = new TextBlock
            {
                Text = label,
                FontSize = 12,
                Foreground = new SolidColorBrush(CText),
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 0, 10, 0),
            };
            Grid.SetColumn(title, 0);
            row.Children.Add(title);

            var readout = new Border
            {
                Background = new SolidColorBrush(CSurface2),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(5),
                Padding = new Thickness(0, 3, 0, 3),
                VerticalAlignment = VerticalAlignment.Center,
            };
            var readoutText = new TextBlock
            {
                Text = value.ToString(format, CultureInfo.InvariantCulture),
                FontSize = 11.5,
                Foreground = new SolidColorBrush(enabled ? CPrimaryHi : CDim),
                HorizontalAlignment = HorizontalAlignment.Center,
                FontFamily = FMono,
            };
            readout.Child = readoutText;
            Grid.SetColumn(readout, 2);
            row.Children.Add(readout);

            var slider = new Slider
            {
                Minimum = min,
                Maximum = max,
                SmallChange = step,
                LargeChange = step * 10,
                Value = value,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(0, 0, 12, 0),
                IsMoveToPointEnabled = true,
                IsEnabled = enabled,
                Focusable = false,
            };
            StudioStyleSlider(slider);
            Grid.SetColumn(slider, 1);
            row.Children.Add(slider);

            slider.ValueChanged += delegate
            {
                double snapped = Math.Round(slider.Value / step) * step;
                set(snapped);
                readoutText.Text = snapped.ToString(format, CultureInfo.InvariantCulture);
                // Applied live, so the desktop shows the change while the slider moves.
                manager.RefreshOptions();
                StudioRefreshPreview();
            };

            return row;
        }

        /// <summary>
        /// Replaces the stock slider template: a 4px trough, a crimson fill up to the
        /// thumb, and a round thumb with a glow.
        ///
        /// Written as XAML rather than as FrameworkElementFactory calls because Track's
        /// parts (Thumb, DecreaseRepeatButton, IncreaseRepeatButton) are plain CLR
        /// properties, not DependencyProperties - FrameworkElementFactory.SetValue cannot
        /// set them, and there is no Track.ThumbProperty to pass. XAML property-element
        /// syntax sets them the same way the stock template does. Building it by hand
        /// would mean re-implementing Track's hit testing and keyboard handling.
        ///
        /// The colours are the shell's: CPrimary is #FF2E43, CSurface is #10131A.
        /// </summary>
        private static readonly string StudioSliderXaml = @"
<ControlTemplate TargetType=""Slider""
    xmlns=""http://schemas.microsoft.com/winfx/2006/xaml/presentation""
    xmlns:x=""http://schemas.microsoft.com/winfx/2006/xaml"">
  <Grid>
    <Border Height=""4"" CornerRadius=""2"" Background=""#1E232E"" VerticalAlignment=""Center""/>
    <Track x:Name=""PART_Track"" VerticalAlignment=""Center"" Height=""16"">
      <Track.DecreaseRepeatButton>
        <RepeatButton>
          <RepeatButton.Template>
            <ControlTemplate TargetType=""RepeatButton"">
              <Border Height=""4"" CornerRadius=""2"" Background=""#FF2E43"" VerticalAlignment=""Center""/>
            </ControlTemplate>
          </RepeatButton.Template>
        </RepeatButton>
      </Track.DecreaseRepeatButton>
      <Track.IncreaseRepeatButton>
        <RepeatButton>
          <RepeatButton.Template>
            <ControlTemplate TargetType=""RepeatButton"">
              <Border Height=""4"" CornerRadius=""2"" Background=""Transparent""/>
            </ControlTemplate>
          </RepeatButton.Template>
        </RepeatButton>
      </Track.IncreaseRepeatButton>
      <Track.Thumb>
        <Thumb>
          <Thumb.Template>
            <ControlTemplate TargetType=""Thumb"">
              <Border Width=""15"" Height=""15"" CornerRadius=""8"" Background=""#F2F5FA""
                      BorderBrush=""#FF2E43"" BorderThickness=""2.5"">
                <Border.Effect>
                  <DropShadowEffect Color=""#FF2E43"" BlurRadius=""10"" ShadowDepth=""0"" Opacity=""0.7""/>
                </Border.Effect>
              </Border>
            </ControlTemplate>
          </Thumb.Template>
        </Thumb>
      </Track.Thumb>
    </Track>
  </Grid>
</ControlTemplate>";

        private void StudioStyleSlider(Slider slider)
        {
            // Parsed once and cached: a page of twelve sliders would otherwise re-parse the
            // same string twelve times on every page switch.
            if (studioSliderTemplate == null)
            {
                studioSliderTemplate = (ControlTemplate)System.Windows.Markup.XamlReader.Parse(StudioSliderXaml);
            }
            slider.Template = studioSliderTemplate;
        }

        /// <summary>A switch with a title and an optional explanatory line.</summary>
        private UIElement StudioToggle(string label, string hint, bool value, Action<bool> set)
        {
            return StudioToggle(label, hint, value, set, false);
        }

        /// <summary>
        /// Satu baris sakelar: label di kiri, sakelar di kanan.
        ///
        /// `susunUlang` menentukan apakah halaman perlu dibangun ulang sesudah
        /// sakelar diubah, dan itu HARUS dipilih dengan benar. Membangun ulang
        /// halaman itu mahal: seluruh pohon elemen dibuang dan dibuat lagi,
        /// halaman berkedip, dan posisi gulir harus dipulihkan. Untuk sakelar
        /// yang hanya mengubah nilai - tanggal, format 12 jam, ping-pong, HDR -
        /// tidak ada satu pun elemen yang berubah, jadi membangun ulang hanya
        /// menghasilkan kedipan.
        ///
        /// Yang benar-benar mengubah susunan halaman hanya sakelar yang
        /// menampilkan atau menyembunyikan bagian lain: menghidupkan jam
        /// memunculkan seluruh pengaturan jam di bawahnya. Untuk yang seperti
        /// itu, membangun ulang memang perlu.
        /// </summary>
        private UIElement StudioToggle(string label, string hint, bool value, Action<bool> set,
                                       bool susunUlang)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 11) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            text.Children.Add(new TextBlock { Text = label, FontSize = 12, Foreground = new SolidColorBrush(CText) });
            if (!string.IsNullOrEmpty(hint))
            {
                text.Children.Add(new TextBlock
                {
                    Text = hint,
                    FontSize = 11,
                    Foreground = new SolidColorBrush(CDim),
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(0, 3, 12, 0),
                });
            }
            Grid.SetColumn(text, 0);
            row.Children.Add(text);

            // A real switch rather than an On/Off button: the button had to be read, and
            // its state was carried only by its colour.
            //
            // It is a CheckBox, not a Border with a click handler.
            //
            // As a Border it was invisible to Windows UI Automation: the whole app exposed
            // 128 Text, 78 Button and 14 Slider elements and not one checkbox, so a screen
            // reader could not tell that these switches existed, could not read their state
            // and could not operate them. Automation tools could not either - the z-order
            // checker could not switch the timer on to test it, and reported "no small
            // LumaWall window found" instead.
            //
            // A CheckBox carries its own toggle state and TogglePattern, so both a screen
            // reader and a checker can read and operate it. The look is unchanged: the
            // default template is replaced by the same track-and-knob drawing.
            var box = new CheckBox
            {
                IsChecked = value,
                Width = 42,
                Height = 23,
                Cursor = Cursors.Hand,
                VerticalAlignment = VerticalAlignment.Center,
                Focusable = true,
                ToolTip = label,
            };
            System.Windows.Automation.AutomationProperties.SetName(box, label);
            if (!string.IsNullOrEmpty(hint))
                System.Windows.Automation.AutomationProperties.SetHelpText(box, hint);

            var track = new Border
            {
                Width = 42,
                Height = 23,
                CornerRadius = new CornerRadius(12),
                Background = new SolidColorBrush(value ? CPrimary : Color.FromRgb(38, 44, 58)),
                BorderBrush = new SolidColorBrush(value ? CPrimaryHi : CBorder),
                BorderThickness = new Thickness(1),
            };
            var knob = new Border
            {
                Width = 15,
                Height = 15,
                CornerRadius = new CornerRadius(8),
                Background = Brushes.White,
                HorizontalAlignment = value ? HorizontalAlignment.Right : HorizontalAlignment.Left,
                Margin = new Thickness(3, 0, 3, 0),
                VerticalAlignment = VerticalAlignment.Center,
                // Bayangan tipis di bawah knob: itu yang membuat sakelar terbaca
                // sebagai benda yang bisa digeser, bukan sebagai dua kotak.
                Effect = new DropShadowEffect
                {
                    Color = Colors.Black,
                    BlurRadius = 4,
                    ShadowDepth = 1,
                    Opacity = 0.45,
                    Direction = 270,
                },
            };
            track.Child = knob;

            // Template CheckBox DIGANTI, bukan hanya isinya.
            //
            // `box.Content = track` saja tidak cukup, dan itu penyebab sakelarnya
            // terlihat seperti kotak centang: template bawaan WPF menggambar
            // kotak centangnya SENDIRI di samping konten, jadi yang terlihat di
            // layar adalah kotak centang dengan sakelar kecil di sebelahnya.
            // Yang benar adalah mengganti ControlTemplate-nya sehingga yang
            // digambar hanyalah track dan knob - dan CheckBox tetap membawa
            // status serta TogglePattern-nya, yang dibutuhkan screen reader dan
            // alat pemeriksa.
            var templat = new ControlTemplate(typeof(CheckBox));
            var isi = new FrameworkElementFactory(typeof(ContentPresenter));
            isi.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
            isi.SetValue(ContentPresenter.VerticalAlignmentProperty, VerticalAlignment.Center);
            templat.VisualTree = isi;
            box.Template = templat;
            box.Content = track;
            box.Background = Brushes.Transparent;
            box.BorderThickness = new Thickness(0);
            box.Padding = new Thickness(0);
            box.HorizontalContentAlignment = HorizontalAlignment.Center;
            box.VerticalContentAlignment = VerticalAlignment.Center;

            // Paint the switch from its own state, so a change made by a screen reader or an
            // automation tool looks exactly like a change made by a click.
            Action paint = delegate
            {
                bool on = box.IsChecked == true;
                track.Background = new SolidColorBrush(on ? CPrimary : Color.FromRgb(38, 44, 58));
                track.BorderBrush = new SolidColorBrush(on ? CPrimaryHi : CBorder);
                knob.HorizontalAlignment = on ? HorizontalAlignment.Right : HorizontalAlignment.Left;
            };

            box.Checked += delegate
            {
                paint();
                set(true);
                manager.RefreshOptions();
                store.Save(config);
                if (susunUlang) ReloadCurrentPage();
            };
            box.Unchecked += delegate
            {
                paint();
                set(false);
                manager.RefreshOptions();
                store.Save(config);
                if (susunUlang) ReloadCurrentPage();
            };

            Grid.SetColumn(box, 1);
            row.Children.Add(box);

            return row;
        }

        /// <summary>A line of text with one or two buttons beside it.</summary>
        private UIElement StudioActionRow(string text, string primaryLabel, RoutedEventHandler primaryClick,
            string secondaryLabel, RoutedEventHandler secondaryClick)
        {
            var grid = new Grid { Margin = new Thickness(0, 0, 0, 8) };
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            if (secondaryLabel != null) grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var label = new TextBlock
            {
                Text = text,
                FontSize = 12.5,
                Foreground = new SolidColorBrush(CText),
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 0, 8, 0),
            };
            Grid.SetColumn(label, 0);
            grid.Children.Add(label);

            var first = GhostButton(primaryLabel);
            first.Height = 31;
            first.FontSize = 11.5;
            // Guarded: a null handler would throw ArgumentNullException("handler") here, and
            // that is exactly how the page crashed on open once already.
            if (primaryClick != null) first.Click += primaryClick;
            Grid.SetColumn(first, 1);
            grid.Children.Add(first);

            if (secondaryLabel != null)
            {
                var second = GhostButton(secondaryLabel);
                second.Height = 31;
                second.FontSize = 11.5;
                second.Margin = new Thickness(8, 0, 0, 0);
                if (secondaryClick != null) second.Click += secondaryClick;
                Grid.SetColumn(second, 2);
                grid.Children.Add(second);
            }
            return grid;
        }

        private UIElement StudioResetRow()
        {
            var row = new WrapPanel();
            var reset = GhostButton(Tr("studio.reset"));
            reset.Height = 31;
            reset.FontSize = 11.5;
            reset.Margin = new Thickness(0, 0, 8, 6);
            reset.Click += delegate
            {
                config.Displays[studioDevice] = new DisplayOptions();
                manager.RefreshOptions();
                store.Save(config);
                ReloadCurrentPage();
            };
            row.Children.Add(reset);

            var resetAll = GhostButton(Tr("studio.resetAll"));
            resetAll.Height = 31;
            resetAll.FontSize = 11.5;
            resetAll.Margin = new Thickness(0, 0, 8, 6);
            resetAll.Click += delegate
            {
                config.Displays.Clear();
                manager.RefreshOptions();
                store.Save(config);
                ReloadCurrentPage();
            };
            row.Children.Add(resetAll);
            return row;
        }

        /// <summary>
        /// The reset card, on its own at the foot of the left column.
        ///
        /// A card rather than a bare row of buttons: "reset everything" throws away every
        /// display's grade, and a button that destructive should not look like the chips
        /// above it. The note says what each one does before it is pressed.
        /// </summary>
        private UIElement StudioResetCard()
        {
            Border card;
            var host = StudioCard(Tr("studio.reset"), Tr("studio.resetHint"), Icons.Reset, CStudioAccent, out card);
            host.Children.Add(StudioResetRow());
            return card;
        }

        // ── presets and the preview ──────────────────────────────────────────────────

        /// <summary>
        /// The built-in looks. Each is a whole grade, so one click gives a result that
        /// would otherwise take four sliders and a filter to reach.
        ///
        /// Fields: name, brightness, contrast, saturation, hue, gamma, filter.
        /// </summary>
        private static IEnumerable<string[]> StudioPresets()
        {
            yield return new[] { "natural", "1.00", "1.00", "1.00", "0", "1.00", "none" };
            yield return new[] { "vivid", "1.06", "1.14", "1.34", "0", "1.00", "vivid" };
            yield return new[] { "cinema", "0.98", "1.16", "0.94", "-6", "1.06", "noir" };
            yield return new[] { "warm", "1.04", "1.02", "1.10", "12", "1.00", "warm" };
            yield return new[] { "night", "0.86", "1.08", "0.88", "-14", "0.94", "cool" };
            yield return new[] { "soft", "1.08", "0.94", "1.06", "0", "0.92", "dream" };
        }

        private void StudioApplyPreset(string[] preset)
        {
            DisplayOptions target = config.OptionsFor(studioDevice);
            target.Brightness = double.Parse(preset[1], CultureInfo.InvariantCulture);
            target.Contrast = double.Parse(preset[2], CultureInfo.InvariantCulture);
            target.Saturation = double.Parse(preset[3], CultureInfo.InvariantCulture);
            target.Hue = double.Parse(preset[4], CultureInfo.InvariantCulture);
            target.Gamma = double.Parse(preset[5], CultureInfo.InvariantCulture);
            target.Filter = preset[6];
        }

        /// <summary>
        /// Repaints the preview from the current options.
        ///
        /// Called on every slider move. It only touches two elements, so it is cheap
        /// enough to run inside a drag - which is the point, because a preview that lags
        /// the slider is worse than none.
        /// </summary>
        private void StudioRefreshPreview()
        {
            if (studioPreviewSwatch == null) return;
            DisplayOptions options = config.OptionsFor(studioDevice);

            var brush = new LinearGradientBrush { StartPoint = new Point(0, 0), EndPoint = new Point(1, 1) };
            brush.GradientStops.Add(new GradientStop(StudioGradeColour(Color.FromRgb(26, 38, 66), options), 0.0));
            brush.GradientStops.Add(new GradientStop(StudioGradeColour(Color.FromRgb(146, 84, 116), options), 0.55));
            brush.GradientStops.Add(new GradientStop(StudioGradeColour(Color.FromRgb(238, 186, 148), options), 1.0));

            // The grade already folds in brightness and hue; the swatch is the brush itself
            // rather than an effect on top of it, so what is shown is what was computed.
            studioPreviewSwatch.Background = brush;

            if (studioPreviewSummary != null)
            {
                studioPreviewSummary.Text = StudioSummary(options);
            }
        }

        /// <summary>Applies brightness, contrast, saturation, hue, gamma and the filter to one colour.</summary>
        private static Color StudioGradeColour(Color colour, DisplayOptions options)
        {
            double r = colour.R / 255.0, g = colour.G / 255.0, b = colour.B / 255.0;

            // contrast around mid grey, then brightness
            r = (r - 0.5) * options.Contrast + 0.5;
            g = (g - 0.5) * options.Contrast + 0.5;
            b = (b - 0.5) * options.Contrast + 0.5;
            r *= options.Brightness;
            g *= options.Brightness;
            b *= options.Brightness;

            // gamma
            double inv = 1.0 / Math.Max(0.01, options.Gamma);
            r = Math.Pow(Math.Max(0, Math.Min(1, r)), inv);
            g = Math.Pow(Math.Max(0, Math.Min(1, g)), inv);
            b = Math.Pow(Math.Max(0, Math.Min(1, b)), inv);

            // saturation, via luma
            double luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            r = luma + (r - luma) * options.Saturation;
            g = luma + (g - luma) * options.Saturation;
            b = luma + (b - luma) * options.Saturation;

            // hue rotation
            if (Math.Abs(options.Hue) > 0.01)
            {
                double angle = options.Hue * Math.PI / 180.0;
                double cos = Math.Cos(angle), sin = Math.Sin(angle);
                double nr = (0.213 + cos * 0.787 - sin * 0.213) * r + (0.715 - cos * 0.715 - sin * 0.715) * g + (0.072 - cos * 0.072 + sin * 0.928) * b;
                double ng = (0.213 - cos * 0.213 + sin * 0.143) * r + (0.715 + cos * 0.285 + sin * 0.140) * g + (0.072 - cos * 0.072 - sin * 0.283) * b;
                double nb = (0.213 - cos * 0.213 - sin * 0.787) * r + (0.715 - cos * 0.715 + sin * 0.715) * g + (0.072 + cos * 0.928 + sin * 0.072) * b;
                r = nr;
                g = ng;
                b = nb;
            }

            // the filter chips
            switch (options.Filter)
            {
                case "grayscale":
                    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
                    r = g = b = luma;
                    break;
                case "sepia":
                    // The classic matrix, with the intermediates kept so each channel is
                    // computed from the original colour rather than from the one before it.
                    double sr = r * 0.393 + g * 0.769 + b * 0.189;
                    double sg = r * 0.349 + g * 0.686 + b * 0.168;
                    double sb = r * 0.272 + g * 0.534 + b * 0.131;
                    r = sr;
                    g = sg;
                    b = sb;
                    break;
                case "cool":
                    r *= 0.88;
                    b = Math.Min(1, b * 1.18);
                    break;
                case "warm":
                    r = Math.Min(1, r * 1.14);
                    b *= 0.86;
                    break;
                case "vivid":
                    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
                    r = luma + (r - luma) * 1.45;
                    g = luma + (g - luma) * 1.45;
                    b = luma + (b - luma) * 1.45;
                    break;
                case "noir":
                    luma = Math.Pow(Math.Max(0, 0.2126 * r + 0.7152 * g + 0.0722 * b), 0.85) * 1.05;
                    r = g = b = luma;
                    break;
                case "dream":
                    r = Math.Min(1, r * 1.06 + 0.04);
                    g = Math.Min(1, g * 1.03 + 0.03);
                    b = Math.Min(1, b * 1.10 + 0.06);
                    break;
            }

            return Color.FromRgb(
                (byte)Math.Max(0, Math.Min(255, r * 255)),
                (byte)Math.Max(0, Math.Min(255, g * 255)),
                (byte)Math.Max(0, Math.Min(255, b * 255)));
        }

        /// <summary>
        /// The one-line summary under the preview.
        ///
        /// Four values, each with the label that says what it is. An earlier version was
        /// "None · cover · 1x · 1x", where the last two were the playback rate and the
        /// zoom and looked like a repeated value rather than two different settings.
        /// </summary>
        private string StudioSummary(DisplayOptions options)
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{0}  ·  {1}\n{2}  ·  zoom {3}",
                Tr("filter." + options.Filter),
                Tr("fit." + options.Fit),
                Tr("studio.rate") + " " + StudioRateLabel(options.PlaybackRate),
                options.Zoom.ToString("0.##", CultureInfo.InvariantCulture));
        }

        private static string StudioRateLabel(double rate)
        {
            return rate.ToString("0.##", CultureInfo.InvariantCulture) + "x";
        }
    }

    /// <summary>
    /// A display device name without the Win32 prefix.
    ///
    /// The prefix is four characters of escape sequences that mean nothing to a user, and
    /// every label in the Studio page has to show a monitor's name.
    /// </summary>
    internal static class DeviceNameExtensions
    {
        public static string DeviceName(this string device)
        {
            if (string.IsNullOrEmpty(device)) return "";
            return device.Replace("\\\\.\\", "");
        }
    }
}
