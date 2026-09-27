"""Rewrite FeaturesPage.cs against the helpers MainWindow actually has.

The first draft was written against names that seemed reasonable - ChipButton, Card,
CTextDim - and none of them exist. Rather than guess again, the replacements are taken
from the real definitions in MainWindow.cs: SurfaceCard, GhostButton, SettingGroup,
SetRoundedButton, CText, CTextSoft.

The page is rebuilt with those, and one helper is added for the chip row because the app
has no equivalent - a row of mutually exclusive choices is genuinely new here, and
reusing a checkbox for it would misrepresent what the control does.
"""

from pathlib import Path
import re

# ── 1. the replacement page ──────────────────────────────────────────────────
page = r'''// FeaturesPage.cs - the Studio page: look, framing, playback, spans and the timer.
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

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace LumaWall
{
    internal sealed partial class MainWindow
    {
        // Which display the Studio page is editing. A field rather than a local so that
        // leaving the page and returning shows the same monitor, which is what a user
        // expects when comparing two.
        private string studioDevice;

        private UIElement BuildStudio()
        {
            var content = PageCanvas();
            content.Children.Add(PageHeading(Tr("studio.title"), Tr("studio.sub"), null));

            Forms.Screen[] screens = Forms.Screen.AllScreens;
            if (string.IsNullOrEmpty(studioDevice) || !screens.Any(s => s.DeviceName == studioDevice))
                studioDevice = screens.Length > 0 ? screens[0].DeviceName : "";

            content.Children.Add(StudioDisplayPicker(screens));
            if (string.IsNullOrEmpty(studioDevice)) return content;

            content.Children.Add(StudioSpanCard());

            DisplayOptions options = config.OptionsFor(studioDevice);

            // ── look ─────────────────────────────────────────────────────────────
            content.Children.Add(SectionHeader(Tr("studio.look"), null, null));
            content.Children.Add(StudioSlider(Tr("studio.brightness"), 0.2, 2.0, 0.01, options.Brightness, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Brightness = v; }));
            content.Children.Add(StudioSlider(Tr("studio.contrast"), 0.2, 2.0, 0.01, options.Contrast, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Contrast = v; }));
            content.Children.Add(StudioSlider(Tr("studio.saturation"), 0.0, 2.0, 0.01, options.Saturation, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Saturation = v; }));
            content.Children.Add(StudioSlider(Tr("studio.hue"), -180, 180, 1, options.Hue, "F0",
                delegate(double v) { config.OptionsFor(studioDevice).Hue = v; }));
            content.Children.Add(StudioSlider(Tr("studio.gamma"), 0.4, 2.2, 0.01, options.Gamma, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Gamma = v; }));

            content.Children.Add(StudioChips(Tr("studio.filter"),
                new string[] { "none", "grayscale", "sepia", "cool", "warm", "vivid", "noir", "dream" },
                new string[] { Tr("filter.none"), Tr("filter.grayscale"), Tr("filter.sepia"), Tr("filter.cool"),
                               Tr("filter.warm"), Tr("filter.vivid"), Tr("filter.noir"), Tr("filter.dream") },
                options.Filter,
                delegate(string value) { config.OptionsFor(studioDevice).Filter = value; }));

            content.Children.Add(StudioChips(Tr("studio.flip"),
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

            // ── HDR ──────────────────────────────────────────────────────────────
            content.Children.Add(SectionHeader(Tr("studio.hdr"), null, null));
            content.Children.Add(StudioToggle(Tr("studio.hdrOn"), Tr("studio.hdrHint"), options.HdrToneMap,
                delegate(bool v) { config.OptionsFor(studioDevice).HdrToneMap = v; }));
            content.Children.Add(StudioSlider(Tr("studio.hdrExposure"), -1.0, 1.0, 0.01, options.HdrExposure, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).HdrExposure = v; }));
            content.Children.Add(StudioSlider(Tr("studio.hdrHighlight"), 0.1, 1.0, 0.01, options.HdrHighlight, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).HdrHighlight = v; }));

            // ── framing ──────────────────────────────────────────────────────────
            content.Children.Add(SectionHeader(Tr("studio.framing"), null, null));
            content.Children.Add(StudioChips(Tr("studio.fit"),
                new string[] { "cover", "contain", "fill", "center" },
                new string[] { Tr("fit.cover"), Tr("fit.contain"), Tr("fit.fill"), Tr("fit.center") },
                options.Fit,
                delegate(string value) { config.OptionsFor(studioDevice).Fit = value; }));
            content.Children.Add(StudioSlider(Tr("studio.zoom"), 0.5, 3.0, 0.01, options.Zoom, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).Zoom = v; }));
            content.Children.Add(StudioSlider(Tr("studio.panX"), -1.0, 1.0, 0.01, options.OffsetX, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).OffsetX = v; }));
            content.Children.Add(StudioSlider(Tr("studio.panY"), -1.0, 1.0, 0.01, options.OffsetY, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).OffsetY = v; }));

            // ── playback ─────────────────────────────────────────────────────────
            content.Children.Add(SectionHeader(Tr("studio.playback"), null, null));
            content.Children.Add(StudioSlider(Tr("studio.rate"), 0.25, 4.0, 0.05, options.PlaybackRate, "F2",
                delegate(double v) { config.OptionsFor(studioDevice).PlaybackRate = v; }));
            content.Children.Add(StudioToggle(Tr("studio.pingpong"), Tr("studio.pingpongHint"), options.PingPong,
                delegate(bool v) { config.OptionsFor(studioDevice).PingPong = v; }));
            content.Children.Add(StudioResetRow());

            // ── the timer ────────────────────────────────────────────────────────
            content.Children.Add(SectionHeader(Tr("studio.timer"), null, null));
            content.Children.Add(BuildTimerSection());

            return content;
        }

        /// <summary>
        /// The monitor selector.
        ///
        /// A row of chips rather than a dropdown: the number of monitors is small, and a
        /// combo box would hide which display the controls below apply to.
        /// </summary>
        private UIElement StudioDisplayPicker(Forms.Screen[] screens)
        {
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            card.Child = StudioStack(new UIElement[]
            {
                StudioLabel(Tr("studio.display")),
                StudioChipRow(
                    screens.Select(s => s.DeviceName).ToArray(),
                    screens.Select(s => (s.Primary ? Tr("studio.primary") + " · " : "") + s.DeviceName.Replace("\\\\.\\", "")).ToArray(),
                    studioDevice,
                    delegate(string device) { studioDevice = device; }),
            });
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
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            var stack = new StackPanel();
            stack.Children.Add(StudioLabel(Tr("studio.span")));
            stack.Children.Add(StudioHint(Tr("studio.spanHint")));

            Forms.Screen[] screens = Forms.Screen.AllScreens;
            if (screens.Length < 2)
            {
                stack.Children.Add(StudioHint(Tr("studio.spanSingle")));
                card.Child = stack;
                return card;
            }

            foreach (SpanGroup group in config.SpanGroups.ToList())
            {
                SpanGroup captured = group;
                string names = string.Join(" + ", captured.Devices.Select(d => d.DeviceName()));
                stack.Children.Add(StudioActionRow(
                    (captured.Enabled ? "● " : "○ ") + names + "   ·   " + Path.GetFileNameWithoutExtension(captured.Path ?? ""),
                    captured.Enabled ? Tr("studio.spanOff") : Tr("studio.spanOn"),
                    delegate
                    {
                        if (captured.Enabled) ClearSpanGroup(captured);
                        else ApplySpanGroup(captured);
                        store.Save(config);
                        SwitchPage("studio");
                    },
                    Tr("studio.remove"),
                    delegate
                    {
                        ClearSpanGroup(captured);
                        config.SpanGroups.Remove(captured);
                        store.Save(config);
                        SwitchPage("studio");
                    }));
            }

            var create = new WrapPanel { Margin = new Thickness(0, 4, 0, 0) };
            foreach (Forms.Screen other in screens)
            {
                if (other.DeviceName == studioDevice) continue;
                Forms.Screen captured = other;
                var make = GhostButton(string.Format(CultureInfo.InvariantCulture, Tr("studio.spanWith"),
                    captured.DeviceName.Replace("\\\\.\\", "")));
                make.Margin = new Thickness(0, 0, 8, 8);
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
                    SwitchPage("studio");
                };
                create.Children.Add(make);
            }
            stack.Children.Add(create);

            SpanGroup active = config.SpanGroupFor(studioDevice);
            if (active != null)
            {
                var line = StudioHint(string.Format(CultureInfo.InvariantCulture, Tr("studio.spanActive"),
                    Path.GetFileNameWithoutExtension(active.Path ?? "")));
                line.Foreground = new SolidColorBrush(CPrimaryHi);
                stack.Children.Add(line);
            }

            card.Child = stack;
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

        // ── controls ─────────────────────────────────────────────────────────────

        private TextBlock StudioLabel(string text)
        {
            return new TextBlock
            {
                Text = text,
                FontSize = 13,
                FontWeight = FontWeights.SemiBold,
                Foreground = new SolidColorBrush(CText),
                Margin = new Thickness(0, 0, 0, 8),
            };
        }

        private TextBlock StudioHint(string text)
        {
            return new TextBlock
            {
                Text = text,
                FontSize = 11.5,
                Foreground = new SolidColorBrush(CTextSoft),
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            };
        }

        private static StackPanel StudioStack(UIElement[] children)
        {
            var stack = new StackPanel();
            foreach (UIElement child in children) stack.Children.Add(child);
            return stack;
        }

        /// <summary>A row of mutually exclusive chips that applies on click.</summary>
        private UIElement StudioChipRow(string[] keys, string[] labels, string current, Action<string> set)
        {
            var row = new WrapPanel();
            for (int i = 0; i < keys.Length; i++)
            {
                string key = keys[i];
                var button = GhostButton(labels[i]);
                button.Margin = new Thickness(0, 0, 8, 6);
                // The chosen chip is filled with the primary colour: a chip row that does not
                // show which option is active is a row of buttons, not a selector.
                if (key == current)
                {
                    button.Background = new SolidColorBrush(CPrimary);
                    button.Foreground = Brushes.White;
                }
                button.Click += delegate { set(key); };
                row.Children.Add(button);
            }
            return row;
        }

        /// <summary>A labelled slider that applies on every move, not on release.</summary>
        private UIElement StudioSlider(string label, double min, double max, double step, double value, string format,
            Action<double> set)
        {
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(190) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(70) });

            var title = new TextBlock
            {
                Text = label,
                FontSize = 13,
                Foreground = new SolidColorBrush(CText),
                VerticalAlignment = VerticalAlignment.Center,
            };
            Grid.SetColumn(title, 0);
            grid.Children.Add(title);

            var readout = new TextBlock
            {
                Text = value.ToString(format, CultureInfo.InvariantCulture),
                FontSize = 12.5,
                Foreground = new SolidColorBrush(CPrimaryHi),
                VerticalAlignment = VerticalAlignment.Center,
                HorizontalAlignment = HorizontalAlignment.Right,
                FontFamily = FMono,
            };
            Grid.SetColumn(readout, 2);
            grid.Children.Add(readout);

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
            };
            Grid.SetColumn(slider, 1);
            grid.Children.Add(slider);

            slider.ValueChanged += delegate
            {
                double snapped = Math.Round(slider.Value / step) * step;
                set(snapped);
                readout.Text = snapped.ToString(format, CultureInfo.InvariantCulture);
                // Applied live, so the desktop shows the change while the slider moves.
                manager.RefreshOptions();
            };

            card.Child = grid;
            return card;
        }

        private UIElement StudioChips(string label, string[] keys, string[] labels, string current, Action<string> set)
        {
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            card.Child = StudioStack(new UIElement[]
            {
                StudioLabel(label),
                StudioChipRow(keys, labels, current, delegate(string key)
                {
                    set(key);
                    manager.RefreshOptions();
                    store.Save(config);
                    SwitchPage("studio");
                }),
            });
            return card;
        }

        /// <summary>A switch with a title and an explanatory line.</summary>
        private UIElement StudioToggle(string label, string hint, bool value, Action<bool> set)
        {
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            text.Children.Add(new TextBlock { Text = label, FontSize = 13, Foreground = new SolidColorBrush(CText) });
            text.Children.Add(new TextBlock
            {
                Text = hint,
                FontSize = 11.5,
                Foreground = new SolidColorBrush(CTextSoft),
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 12, 0),
            });
            Grid.SetColumn(text, 0);
            grid.Children.Add(text);

            var toggle = GhostButton(value ? Tr("studio.on") : Tr("studio.off"));
            toggle.VerticalAlignment = VerticalAlignment.Center;
            if (value)
            {
                toggle.Background = new SolidColorBrush(CPrimary);
                toggle.Foreground = Brushes.White;
            }
            toggle.Click += delegate
            {
                set(!value);
                manager.RefreshOptions();
                store.Save(config);
                SwitchPage("studio");
            };
            Grid.SetColumn(toggle, 1);
            grid.Children.Add(toggle);

            card.Child = grid;
            return card;
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
            first.Click += primaryClick;
            Grid.SetColumn(first, 1);
            grid.Children.Add(first);

            if (secondaryLabel != null)
            {
                var second = GhostButton(secondaryLabel);
                second.Margin = new Thickness(8, 0, 0, 0);
                second.Click += secondaryClick;
                Grid.SetColumn(second, 2);
                grid.Children.Add(second);
            }
            return grid;
        }

        private UIElement StudioResetRow()
        {
            var row = new WrapPanel { Margin = new Thickness(0, 4, 0, 10) };
            var reset = GhostButton(Tr("studio.reset"));
            reset.Click += delegate
            {
                config.Displays[studioDevice] = new DisplayOptions();
                manager.RefreshOptions();
                store.Save(config);
                SwitchPage("studio");
            };
            row.Children.Add(reset);

            var resetAll = GhostButton(Tr("studio.resetAll"));
            resetAll.Margin = new Thickness(8, 0, 0, 0);
            resetAll.Click += delegate
            {
                config.Displays.Clear();
                manager.RefreshOptions();
                store.Save(config);
                SwitchPage("studio");
            };
            row.Children.Add(resetAll);
            return row;
        }

        // ── the timer ────────────────────────────────────────────────────────────

        private UIElement BuildTimerSection()
        {
            var stack = new StackPanel();
            stack.Children.Add(StudioTimerToggle());
            if (!config.Timer.Enabled) return stack;

            stack.Children.Add(StudioChips(Tr("timer.mode"),
                new string[] { "countdown", "clock", "stopwatch" },
                new string[] { Tr("timer.countdown"), Tr("timer.clock"), Tr("timer.stopwatch") },
                config.Timer.Mode,
                delegate(string value) { config.Timer.Mode = value; }));

            stack.Children.Add(StudioChips(Tr("timer.shape"),
                new string[] { "pill", "circle", "square", "bare" },
                new string[] { Tr("timer.pill"), Tr("timer.circle"), Tr("timer.square"), Tr("timer.bare") },
                config.Timer.Shape,
                delegate(string value) { config.Timer.Shape = value; }));

            stack.Children.Add(StudioChips(Tr("timer.position"),
                new string[] { "top-left", "top-center", "top-right", "middle-left", "middle-center",
                               "middle-right", "bottom-left", "bottom-center", "bottom-right" },
                new string[] { Tr("timer.tl"), Tr("timer.tc"), Tr("timer.tr"), Tr("timer.ml"), Tr("timer.mc"),
                               Tr("timer.mr"), Tr("timer.bl"), Tr("timer.bc"), Tr("timer.br") },
                config.Timer.Position,
                delegate(string value) { config.Timer.Position = value; }));

            stack.Children.Add(StudioSlider(Tr("timer.size"), 50, 250, 5, config.Timer.Scale, "F0",
                delegate(double v) { config.Timer.Scale = (int)v; }));
            stack.Children.Add(StudioSlider(Tr("timer.opacity"), 0.2, 1.0, 0.01, config.Timer.Opacity, "F2",
                delegate(double v) { config.Timer.Opacity = v; }));
            stack.Children.Add(StudioSlider(Tr("timer.offsetX"), -400, 400, 1, config.Timer.OffsetX, "F0",
                delegate(double v) { config.Timer.OffsetX = (int)v; }));
            stack.Children.Add(StudioSlider(Tr("timer.offsetY"), -400, 400, 1, config.Timer.OffsetY, "F0",
                delegate(double v) { config.Timer.OffsetY = (int)v; }));

            if (config.Timer.Mode == "countdown")
            {
                stack.Children.Add(StudioSlider(Tr("timer.length"), 10, 7200, 10, config.Timer.Seconds, "F0",
                    delegate(double v) { config.Timer.Seconds = (int)v; }));
            }

            stack.Children.Add(StudioToggle(Tr("timer.blink"), Tr("timer.blinkHint"), config.Timer.BlinkAtEnd,
                delegate(bool v) { config.Timer.BlinkAtEnd = v; }));

            var actions = new WrapPanel { Margin = new Thickness(0, 4, 0, 10) };
            var restart = GhostButton(Tr("timer.restart"));
            restart.Click += delegate { timerReset(); ShowToast(Tr("timer.restarted")); };
            actions.Children.Add(restart);

            var hold = GhostButton(Tr("timer.pause"));
            hold.Margin = new Thickness(8, 0, 0, 0);
            hold.Click += delegate { timerPause(); };
            actions.Children.Add(hold);
            stack.Children.Add(actions);

            return stack;
        }

        private UIElement StudioTimerToggle()
        {
            var card = SurfaceCard(new Thickness(0, 0, 0, 8));
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            text.Children.Add(new TextBlock { Text = Tr("timer.enable"), FontSize = 13, Foreground = new SolidColorBrush(CText) });
            text.Children.Add(new TextBlock
            {
                Text = Tr("timer.hint"),
                FontSize = 11.5,
                Foreground = new SolidColorBrush(CTextSoft),
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 12, 0),
            });
            Grid.SetColumn(text, 0);
            grid.Children.Add(text);

            var toggle = GhostButton(config.Timer.Enabled ? Tr("studio.on") : Tr("studio.off"));
            toggle.VerticalAlignment = VerticalAlignment.Center;
            if (config.Timer.Enabled)
            {
                toggle.Background = new SolidColorBrush(CPrimary);
                toggle.Foreground = Brushes.White;
            }
            toggle.Click += delegate
            {
                config.Timer.Enabled = !config.Timer.Enabled;
                timerRefresh();
                store.Save(config);
                SwitchPage("studio");
            };
            Grid.SetColumn(toggle, 1);
            grid.Children.Add(toggle);

            card.Child = grid;
            return card;
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
'''

Path('LumaWall/FeaturesPage.cs').write_text(page, encoding='utf-8')
print('  FeaturesPage.cs rewritten: %d bytes' % len(page))

# ── 2. add the file to the project ───────────────────────────────────────────
csproj = Path('LumaWall/LumaWall.csproj')
with csproj.open(encoding='utf-8', newline='') as handle:
    proj = handle.read()
if 'FeaturesPage.cs' not in proj:
    proj = proj.replace(
        '    <Compile Include="DesktopTimer.cs" />\r\n',
        '    <Compile Include="DesktopTimer.cs" />\r\n    <Compile Include="FeaturesPage.cs" />\r\n', 1)
    with csproj.open('w', encoding='utf-8', newline='') as handle:
        handle.write(proj)
print('  csproj includes FeaturesPage: %s' % ('FeaturesPage.cs' in proj))
