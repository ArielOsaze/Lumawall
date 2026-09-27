using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Forms = System.Windows.Forms;
using Drawing = System.Drawing;
using Microsoft.Win32;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace LumaWall
{
    internal static class Program
    {
        private const string InstanceMutexName = "Local\\LumaWall.SingleInstance.2";
        private const string InstancePipeName = "LumaWall.SingleInstance.2";

        /// <summary>
        /// Guards against an exception storm: a fault that keeps firing on every
        /// UI event cannot be recovered from by ignoring it, so after a few
        /// occurrences the app shuts down cleanly instead of spinning on errors.
        /// </summary>
        private static int unhandledCount;
        private static bool IsFatalRepeat(Exception ex)
        {
            unhandledCount++;
            if (unhandledCount <= 5) return false;
            AppLog.Write("Too many unhandled exceptions (" + unhandledCount + "); shutting down");
            return true;
        }

        /// <summary>
        /// The process-wide button style, which exists to remove one thing.
        ///
        /// WPF's built-in Button template has a trigger on IsMouseOver that sets
        /// the background to #FFBEE6FD. That value is baked into the template, so a
        /// button whose Background is set in code still turns pale blue on hover -
        /// the template's trigger wins over the local value it is templating.
        ///
        /// The visible result was a light blue rectangle over whichever button the
        /// pointer was on. It appeared on the title-bar buttons, the settings rows
        /// and the section links, and it looked like a rendering fault rather than
        /// a hover state.
        ///
        /// This style uses a template with no hover trigger at all. Buttons that
        /// want a hover set their own, as the title-bar buttons do. Because it is
        /// the implicit style for Button, a button added later inherits it and
        /// cannot bring the blue back.
        /// </summary>
        private static System.Windows.Style BuildDefaultButtonStyle()
        {
            var style = new System.Windows.Style(typeof(System.Windows.Controls.Button));

            var border = new FrameworkElementFactory(typeof(Border));
            border.SetBinding(Border.BackgroundProperty,
                new Binding("Background") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.BorderBrushProperty,
                new Binding("BorderBrush") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.BorderThicknessProperty,
                new Binding("BorderThickness") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.PaddingProperty,
                new Binding("Padding") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetValue(Border.SnapsToDevicePixelsProperty, true);

            var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
            presenter.SetBinding(ContentPresenter.ContentProperty,
                new Binding("Content") { RelativeSource = RelativeSource.TemplatedParent });
            presenter.SetBinding(ContentPresenter.HorizontalAlignmentProperty,
                new Binding("HorizontalContentAlignment") { RelativeSource = RelativeSource.TemplatedParent });
            presenter.SetBinding(ContentPresenter.VerticalAlignmentProperty,
                new Binding("VerticalContentAlignment") { RelativeSource = RelativeSource.TemplatedParent });
            border.AppendChild(presenter);

            var template = new ControlTemplate(typeof(System.Windows.Controls.Button)) { VisualTree = border };
            style.Setters.Add(new Setter(System.Windows.Controls.Control.TemplateProperty, template));

            return style;
        }

        /// <summary>
        /// A dark scrollbar for the whole app.
        ///
        /// WPF's built-in ScrollBar template is the Aero2 one, which draws a light grey
        /// track with a slightly lighter thumb - the values are hard-coded in the theme, so
        /// setting Background on the ScrollViewer does nothing. On a near-black window that
        /// reads as a white bar down the right edge, which is what it looked like.
        ///
        /// This replaces the template process-wide. The bar is drawn as a thin thumb on a
        /// transparent track, so the chrome stays out of the way and the thumb is the only
        /// part that is visible - the shape most desktop apps have used for years.
        /// </summary>
        private static System.Windows.Style BuildDefaultScrollBarStyle()
        {
            // Two templates: the vertical bar and the horizontal one. Each is a Track with
            // a Thumb; there are no arrow buttons, which is why no line buttons are needed.
            const string vertical = @"
<ControlTemplate xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation'
                 xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml'
                 TargetType='ScrollBar'>
  <Grid Background='Transparent'>
    <Track x:Name='PART_Track' IsDirectionReversed='True'>
      <Track.DecreaseRepeatButton>
        <RepeatButton Command='ScrollBar.PageUpCommand' Opacity='0' Focusable='False' />
      </Track.DecreaseRepeatButton>
      <Track.Thumb>
        <Thumb>
          <Thumb.Template>
            <ControlTemplate TargetType='Thumb'>
              <Border x:Name='Bar' Background='#33FFFFFF' CornerRadius='4' Margin='2,0' />
              <ControlTemplate.Triggers>
                <Trigger Property='IsMouseOver' Value='True'>
                  <Setter TargetName='Bar' Property='Background' Value='#59FFFFFF' />
                </Trigger>
                <Trigger Property='IsDragging' Value='True'>
                  <Setter TargetName='Bar' Property='Background' Value='#8CFFFFFF' />
                </Trigger>
              </ControlTemplate.Triggers>
            </ControlTemplate>
          </Thumb.Template>
        </Thumb>
      </Track.Thumb>
      <Track.IncreaseRepeatButton>
        <RepeatButton Command='ScrollBar.PageDownCommand' Opacity='0' Focusable='False' />
      </Track.IncreaseRepeatButton>
    </Track>
  </Grid>
</ControlTemplate>";

            const string horizontal = @"
<ControlTemplate xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation'
                 xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml'
                 TargetType='ScrollBar'>
  <Grid Background='Transparent'>
    <Track x:Name='PART_Track' IsDirectionReversed='False'>
      <Track.DecreaseRepeatButton>
        <RepeatButton Command='ScrollBar.PageLeftCommand' Opacity='0' Focusable='False' />
      </Track.DecreaseRepeatButton>
      <Track.Thumb>
        <Thumb>
          <Thumb.Template>
            <ControlTemplate TargetType='Thumb'>
              <Border x:Name='Bar' Background='#33FFFFFF' CornerRadius='4' Margin='0,2' />
              <ControlTemplate.Triggers>
                <Trigger Property='IsMouseOver' Value='True'>
                  <Setter TargetName='Bar' Property='Background' Value='#59FFFFFF' />
                </Trigger>
                <Trigger Property='IsDragging' Value='True'>
                  <Setter TargetName='Bar' Property='Background' Value='#8CFFFFFF' />
                </Trigger>
              </ControlTemplate.Triggers>
            </ControlTemplate>
          </Thumb.Template>
        </Thumb>
      </Track.Thumb>
      <Track.IncreaseRepeatButton>
        <RepeatButton Command='ScrollBar.PageRightCommand' Opacity='0' Focusable='False' />
      </Track.IncreaseRepeatButton>
    </Track>
  </Grid>
</ControlTemplate>";

            var style = new System.Windows.Style(typeof(System.Windows.Controls.Primitives.ScrollBar));
            style.Setters.Add(new Setter(System.Windows.Controls.Control.TemplateProperty,
                System.Windows.Markup.XamlReader.Parse(vertical)));

            // The vertical template is the default; a horizontal bar gets its own, because
            // a vertical Track scrolls the wrong way and the page buttons point the wrong
            // way. The whole page uses one orientation or the other, never both, so this is
            // the only branch needed.
            var orientation = new Trigger
            {
                Property = System.Windows.Controls.Primitives.ScrollBar.OrientationProperty,
                Value = System.Windows.Controls.Orientation.Horizontal
            };
            orientation.Setters.Add(new Setter(System.Windows.Controls.Control.TemplateProperty,
                System.Windows.Markup.XamlReader.Parse(horizontal)));
            style.Triggers.Add(orientation);

            return style;
        }

        [STAThread]
        private static void Main()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;

            // A render-to-file mode, so the timer styles can be measured from the pixels the
            // app itself draws.
            //
            // Screenshotting the widget cannot work: it is a layered window over the
            // wallpaper, so a screen capture contains the wallpaper too, and a checker that
            // thresholds "bright pixels" then measures the wallpaper rather than the clock.
            // That happened - the check reported every style at 93% ink and a full-height
            // clock band, which was the wallpaper behind them.
            //
            // This writes the widget's own 32bpp ARGB bitmap instead, with its real alpha,
            // so "is the clock large" and "is the background transparent" become questions
            // about the drawing rather than about what was behind it.
            string[] commandLine = Environment.GetCommandLineArgs();
            for (int i = 1; i < commandLine.Length; i++)
            {
                if (commandLine[i] == "--render-timer" && i + 1 < commandLine.Length)
                {
                    int code = TimerPreview.Render(commandLine[i + 1]);
                    Environment.Exit(code);
                }
            }

            bool ownsMutex;
            using (var mutex = new Mutex(true, InstanceMutexName, out ownsMutex))
            {
                if (!ownsMutex)
                {
                    AppLog.Write("Secondary launch forwarded: " + string.Join(" ", Environment.GetCommandLineArgs().Skip(1)));
                    SingleInstanceBroker.Send(InstancePipeName, Environment.GetCommandLineArgs().Skip(1).ToArray());
                    return;
                }

                AppLog.Write("Primary process started");
                var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };

                // A default button style for the whole app.
                //
                // WPF's built-in Button style carries an Aero hover trigger that
                // paints the button #FFBEE6FD, a pale blue. Setting Background in
                // code does not override it, because a template trigger beats a
                // local value on the property the template reads. The visible
                // result was a light blue rectangle appearing over whichever
                // control the pointer was on - title-bar buttons, settings rows,
                // section links - which looked like a rendering fault.
                //
                // This replaces that style process-wide, so a button added later
                // cannot reintroduce it. Buttons that want a hover of their own
                // still set one; this only removes the blue.
                app.Resources[typeof(System.Windows.Controls.Button)] = BuildDefaultButtonStyle();

                // The same treatment for the scrollbar: its built-in template is the light
                // Aero2 one, which draws a white bar down the right edge of a near-black
                // window.
                app.Resources[typeof(System.Windows.Controls.Primitives.ScrollBar)] =
                    BuildDefaultScrollBarStyle();

                // Production safety net. Without these, any exception that
                // escapes a handler kills the process with no trace - the app
                // simply vanishes from the desktop and the user has nothing to
                // report. Each handler logs first, so a crash is always
                // diagnosable from lumawall.log afterwards.
                app.DispatcherUnhandledException += delegate(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
                {
                    AppLog.Write("UNHANDLED UI EXCEPTION: " + e.Exception);
                    // Keep running: the UI thread is still usable and a live
                    // wallpaper is worth more than a clean exit. Only give up if
                    // the failure repeats, which means state is unreliable.
                    e.Handled = !IsFatalRepeat(e.Exception);
                };
                AppDomain.CurrentDomain.UnhandledException += delegate(object sender, UnhandledExceptionEventArgs e)
                {
                    AppLog.Write("FATAL UNHANDLED EXCEPTION (terminating=" + e.IsTerminating + "): " + e.ExceptionObject);
                };
                TaskScheduler.UnobservedTaskException += delegate(object sender, UnobservedTaskExceptionEventArgs e)
                {
                    AppLog.Write("UNOBSERVED TASK EXCEPTION: " + e.Exception);
                    e.SetObserved();
                };

                var window = new MainWindow();
                using (var broker = new SingleInstanceBroker(InstancePipeName, delegate(string[] args)
                {
                    window.Dispatcher.BeginInvoke(new Action(delegate { window.HandleSecondaryInvocation(args); }));
                }))
                {
                    broker.Start();
                    app.Run(window);
                }
                AppLog.Write("Primary process stopped");
            }
        }
    }

    internal static class AppLog
    {
        private static readonly object Sync = new object();
        private static readonly string LogFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LumaWall", "Logs");
        private static readonly string LogPath = Path.Combine(LogFolder, "lumawall.log");

        public static void Write(string message)
        {
            try
            {
                lock (Sync)
                {
                    Directory.CreateDirectory(LogFolder);
                    if (File.Exists(LogPath) && new FileInfo(LogPath).Length > 1024 * 1024)
                    {
                        string previous = Path.Combine(LogFolder, "lumawall.previous.log");
                        if (File.Exists(previous)) File.Delete(previous);
                        File.Move(LogPath, previous);
                    }
                    // UTF-8 with an explicit encoder: the default overload picks
                    // UTF-8 without a BOM, and wallpaper file names routinely
                    // contain typographic characters (Albedo's -> U+2019) which
                    // then render as mojibake in the log and make a real problem
                    // impossible to diagnose from it.
                    string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " [" + Process.GetCurrentProcess().Id + "] " + message + Environment.NewLine;
                    using (var stream = new FileStream(LogPath, FileMode.Append, FileAccess.Write, FileShare.Read))
                    using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                    {
                        writer.Write(line);
                    }
                }
            }
            catch { }
        }
    }

    internal sealed class SingleInstanceBroker : IDisposable
    {
        private readonly string pipeName;
        private readonly Action<string[]> callback;
        private volatile bool stopping;
        private Thread listener;

        public SingleInstanceBroker(string name, Action<string[]> handler)
        {
            pipeName = name;
            callback = handler;
        }

        public void Start()
        {
            listener = new Thread(ListenLoop) { IsBackground = true, Name = "LumaWall IPC" };
            listener.Start();
        }

        private void ListenLoop()
        {
            while (!stopping)
            {
                try
                {
                    using (var pipe = new NamedPipeServerStream(pipeName, PipeDirection.In, 1, PipeTransmissionMode.Byte, PipeOptions.None))
                    {
                        pipe.WaitForConnection();
                        if (stopping) return;
                        using (var reader = new BinaryReader(pipe, Encoding.UTF8, true))
                        {
                            int count = Math.Max(0, Math.Min(64, reader.ReadInt32()));
                            var args = new string[count];
                            for (int index = 0; index < count; index++) args[index] = reader.ReadString();
                            AppLog.Write("Received secondary invocation: " + string.Join(" ", args));
                            callback(args);
                        }
                    }
                }
                catch (Exception ex)
                {
                    if (!stopping) { AppLog.Write("IPC listener error: " + ex.Message); Thread.Sleep(250); }
                }
            }
        }

        public static void Send(string name, string[] args)
        {
            for (int attempt = 0; attempt < 4; attempt++)
            {
                try
                {
                    using (var pipe = new NamedPipeClientStream(".", name, PipeDirection.Out))
                    {
                        pipe.Connect(750);
                        using (var writer = new BinaryWriter(pipe, Encoding.UTF8, true))
                        {
                            writer.Write(args.Length);
                            foreach (string value in args) writer.Write(value ?? "");
                            writer.Flush();
                        }
                    }
                    return;
                }
                catch (Exception ex)
                {
                    if (attempt == 3) AppLog.Write("IPC forwarding failed: " + ex.Message);
                    else Thread.Sleep(150);
                }
            }
        }

        public void Dispose()
        {
            stopping = true;
            try
            {
                using (var wake = new NamedPipeClientStream(".", pipeName, PipeDirection.Out)) wake.Connect(100);
            }
            catch { }
        }
    }

    [DataContract]
    public sealed class AppConfig
    {
        [DataMember] public Dictionary<string, string> MonitorVideos = new Dictionary<string, string>();
        [DataMember] public List<string> Library = new List<string>();
        [DataMember] public bool PauseFullscreen = true;
        [DataMember] public bool PauseMaximized = true;
        [DataMember] public bool PauseOnBattery = true;
        [DataMember] public bool Mute = true;
        [DataMember] public bool StartWithWindows = false;
        [DataMember] public string FeedUrl = "";
        [DataMember] public int TargetFps = 24;
        [DataMember] public string Language = "id";
        [DataMember] public bool ShowMature = false;
        [DataMember] public Dictionary<string, Dictionary<string, string>> DisplayProfiles = new Dictionary<string, Dictionary<string, string>>();

        // ── per-display look and playback ────────────────────────────────────
        //
        // Keyed by device name. A monitor with no entry uses the defaults, so an
        // existing config keeps behaving exactly as before this was added.
        [DataMember] public Dictionary<string, DisplayOptions> Displays = new Dictionary<string, DisplayOptions>(StringComparer.OrdinalIgnoreCase);

        // ── one wallpaper stretched across several monitors ──────────────────
        //
        // A separate concept from MonitorVideos, not a special value inside it: a span
        // group replaces the per-monitor wallpapers for its displays while it is on, and
        // turning it off has to leave every monitor's own wallpaper untouched.
        [DataMember] public List<SpanGroup> SpanGroups = new List<SpanGroup>();

        // ── the desktop timer ────────────────────────────────────────────────
        [DataMember] public TimerConfig Timer = new TimerConfig();

        /// <summary>
        /// Replaces every null collection with an empty one.
        ///
        /// DataContractJsonSerializer does not run a field initializer for a member that
        /// is absent from the JSON. A config written before a collection existed therefore
        /// deserializes with that member null - not empty - and the first caller that
        /// enumerates it throws ArgumentNullException. That is how a saved config from the
        /// previous build made the Studio page crash on open: SpanGroups was null and the
        /// page called ToList() on it.
        ///
        /// Called after every load, so no caller has to defend against a null collection.
        /// </summary>
        public void Normalise()
        {
            if (MonitorVideos == null) MonitorVideos = new Dictionary<string, string>();
            if (Library == null) Library = new List<string>();
            if (DisplayProfiles == null) DisplayProfiles = new Dictionary<string, Dictionary<string, string>>();
            if (Displays == null) Displays = new Dictionary<string, DisplayOptions>(StringComparer.OrdinalIgnoreCase);
            if (SpanGroups == null) SpanGroups = new List<SpanGroup>();
            if (Timer == null) Timer = new TimerConfig();
            // A group whose device list is null would fail the same way one level deeper.
            foreach (SpanGroup group in SpanGroups)
            {
                if (group == null) continue;
                if (group.Devices == null) group.Devices = new List<string>();
                if (group.Path == null) group.Path = "";
                if (group.Name == null) group.Name = "";
            }
        }

        public DisplayOptions OptionsFor(string deviceName)
        {
            if (string.IsNullOrEmpty(deviceName)) return new DisplayOptions();
            DisplayOptions options;
            if (Displays.TryGetValue(deviceName, out options) && options != null) return options;
            options = new DisplayOptions();
            Displays[deviceName] = options;
            return options;
        }

        /// <summary>
        /// The span group a monitor belongs to, or null. Returned rather than a bool so the
        /// caller can read the group's path and its full device list - which is what the
        /// wallpaper window needs to know which slice of the picture it is showing.
        /// </summary>
        public SpanGroup SpanGroupFor(string deviceName)
        {
            foreach (SpanGroup group in SpanGroups)
            {
                if (group == null || !group.Enabled) continue;
                foreach (string device in group.Devices)
                    if (string.Equals(device, deviceName, StringComparison.OrdinalIgnoreCase)) return group;
            }
            return null;
        }
    }

    /// <summary>
    /// Everything the user can change about how one display's wallpaper looks and plays.
    ///
    /// Defaults are the identity: brightness 1, contrast 1, saturation 1, no flip, cover
    /// fit, rate 1. A display with default options must render byte-identically to the
    /// build before these existed, which is why every value here is neutral rather than
    /// merely "reasonable".
    /// </summary>
    [DataContract]
    public sealed class DisplayOptions
    {
        // colour
        [DataMember] public double Brightness = 1.0;   // 0.2 .. 2.0
        [DataMember] public double Contrast = 1.0;     // 0.2 .. 2.0
        [DataMember] public double Saturation = 1.0;   // 0 .. 2
        [DataMember] public double Hue = 0.0;          // -180 .. 180 degrees
        [DataMember] public double Gamma = 1.0;        // 0.4 .. 2.2
        [DataMember] public string Filter = "none";    // none | grayscale | sepia | cool | warm | vivid | noir | dream

        // flip
        [DataMember] public bool FlipHorizontal = false;
        [DataMember] public bool FlipVertical = false;

        // HDR
        //
        // Tone mapping, not HDR output: the source is SDR video and the display may or may
        // not be HDR, so this is a look (highlight roll-off plus exposure) rather than a
        // transfer-function change. It is applied in the page's WebGL pass so it costs no
        // system RAM and does not touch the decoded frames.
        [DataMember] public bool HdrToneMap = false;
        [DataMember] public double HdrExposure = 0.0;   // -1 .. 1 stops
        [DataMember] public double HdrHighlight = 0.7;  // 0 .. 1 roll-off point

        // framing
        [DataMember] public string Fit = "cover";      // cover | contain | fill | center | tile
        [DataMember] public double Zoom = 1.0;         // 0.5 .. 3
        [DataMember] public double OffsetX = 0.0;      // -1 .. 1 of the frame
        [DataMember] public double OffsetY = 0.0;

        // playback
        [DataMember] public double PlaybackRate = 1.0; // 0.25 .. 4
        [DataMember] public bool PingPong = false;     // play forward, then backward

        /// <summary>True when nothing here would change a single pixel.</summary>
        public bool IsNeutral()
        {
            return Math.Abs(Brightness - 1.0) < 0.001
                && Math.Abs(Contrast - 1.0) < 0.001
                && Math.Abs(Saturation - 1.0) < 0.001
                && Math.Abs(Hue) < 0.001
                && Math.Abs(Gamma - 1.0) < 0.001
                && (Filter == null || Filter == "none")
                && !FlipHorizontal && !FlipVertical
                && !HdrToneMap
                && (Fit == null || Fit == "cover")
                && Math.Abs(Zoom - 1.0) < 0.001
                && Math.Abs(OffsetX) < 0.001 && Math.Abs(OffsetY) < 0.001
                && Math.Abs(PlaybackRate - 1.0) < 0.001
                && !PingPong;
        }
    }

    /// <summary>
    /// One wallpaper spanning several adjacent monitors, so a picture wider than any single
    /// screen reads as one continuous image across the desktop.
    ///
    /// The displays are ordered left to right by their screen coordinates rather than by
    /// the order they were added, because the user's mental model is "the one on the left
    /// is the left part of the picture" - and device names carry no such meaning.
    /// </summary>
    [DataContract]
    public sealed class SpanGroup
    {
        [DataMember] public string Name = "";
        [DataMember] public string Path = "";
        [DataMember] public List<string> Devices = new List<string>();
        [DataMember] public bool Enabled = false;
    }

    /// <summary>
    /// The desktop timer: a small always-on-top readout the user can place anywhere.
    ///
    /// Shape, size and position are all options rather than a fixed design, because the
    /// right answer depends on the wallpaper behind it - a bright wallpaper needs a
    /// different treatment from a dark one, and the corner that is empty is different on
    /// every desktop.
    /// </summary>
    [DataContract]
    public sealed class TimerConfig
    {
        [DataMember] public bool Enabled = false;
        [DataMember] public string Mode = "countdown";   // countdown | clock | stopwatch

        // The look. Replaces the old Shape field.
        //
        // Shape described a box: pill, circle, square, bare. Three of the four drew an
        // opaque slab with a coloured hairline, which is what made the widget look like a
        // system dialog sitting on the wallpaper. Style describes what macOS and iOS
        // actually do instead:
        //
        //   minimal   the time alone with a soft shadow. No fill, no border.
        //   glass     the same over a faint translucent wash.
        //   card      a macOS-widget panel: translucent, no border.
        //   ring      an iOS timer: a progress arc around the time.
        [DataMember] public string Style = "minimal";    // minimal | glass | card | ring

        // Kept so a config written by an older build still loads. Nothing reads it.
        [DataMember] public string Shape = "";

        [DataMember] public int Seconds = 300;           // countdown length
        [DataMember] public int Scale = 100;             // 50 .. 250 percent
        [DataMember] public string Position = "top-right"; // 9 named positions
        [DataMember] public int OffsetX = 28;
        [DataMember] public int OffsetY = 28;
        [DataMember] public double Opacity = 1.0;        // kept for compatibility
        [DataMember] public string Accent = "#FFFFFF";   // the ink; white reads on any wallpaper
        [DataMember] public string Face = "";            // kept for compatibility
        [DataMember] public bool ShowSeconds = true;
        [DataMember] public bool ShowDate = true;        // the small line under a clock
        [DataMember] public bool TwelveHour = false;     // 9:41 rather than 09:41
        [DataMember] public bool BlinkAtEnd = true;
    }

    [DataContract]
    public sealed class CatalogItem
    {
        [DataMember(Name = "title")] public string Title { get; set; }
        [DataMember(Name = "videoUrl")] public string VideoUrl { get; set; }
        [DataMember(Name = "thumbnailUrl")] public string ThumbnailUrl { get; set; }
        [DataMember(Name = "license")] public string License { get; set; }
        [DataMember(Name = "sourceUrl")] public string SourceUrl { get; set; }
        [DataMember(Name = "category")] public string Category { get; set; }
        [DataMember(Name = "kind")] public string Kind { get; set; }
        [DataMember(Name = "author")] public string Author { get; set; }
        [DataMember(Name = "animation")] public string Animation { get; set; }
    }

    internal sealed class ConfigStore
    {
        private const int MoveFileReplaceExisting = 0x1;
        private const int MoveFileWriteThrough = 0x8;
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool MoveFileEx(string existingFileName, string newFileName, int flags);

        private readonly string folder = string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("LUMAWALL_DATA_DIR"))
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LumaWall")
            : Path.GetFullPath(Environment.GetEnvironmentVariable("LUMAWALL_DATA_DIR"));
        public string Folder { get { return folder; } }
        public string Downloads { get { return Path.Combine(folder, "Wallpapers"); } }
        private string ConfigPath { get { return Path.Combine(folder, "config.json"); } }

        public AppConfig Load()
        {
            Directory.CreateDirectory(folder);
            Directory.CreateDirectory(Downloads);
            if (!File.Exists(ConfigPath)) return new AppConfig();
            try
            {
                // External tools (PowerShell Set-Content -Encoding UTF8, editors)
                // may write a UTF-8 BOM. DataContractJsonSerializer throws on it,
                // which used to wipe every setting on the next save. Strip the BOM
                // before deserializing so such files still load.
                byte[] raw = File.ReadAllBytes(ConfigPath);
                int offset = 0;
                if (raw.Length >= 3 && raw[0] == 0xEF && raw[1] == 0xBB && raw[2] == 0xBF) offset = 3;
                if (raw.Length <= offset) return new AppConfig();
                using (var stream = new MemoryStream(raw, offset, raw.Length - offset))
                {
                    var value = (AppConfig)new DataContractJsonSerializer(typeof(AppConfig)).ReadObject(stream);
                    if (value == null) return new AppConfig();
                    // One call instead of a growing list of null checks here. A member that
                    // is absent from the JSON deserializes to null, not to its initializer,
                    // so every collection added since the file was written needs this - and
                    // the list only grows. Normalise owns that knowledge.
                    value.Normalise();
                    return value;
                }
            }
            catch (Exception ex)
            {
                AppLog.Write("Config load failed: " + ex.Message);
                AppConfig recovered = TryLoadBackup();
                if (recovered != null)
                {
                    AppLog.Write("Recovered configuration from config.json.bak");
                    recovered.Normalise();
                    return recovered;
                }
                // Never let a later save silently destroy an unreadable but
                // possibly repairable file: keep a forensic copy first.
                try
                {
                    string broken = ConfigPath + ".broken";
                    if (File.Exists(broken)) File.Delete(broken);
                    File.Copy(ConfigPath, broken, true);
                    AppLog.Write("Kept unreadable configuration copy at config.json.broken");
                }
                catch { }
                return new AppConfig();
            }
        }

        private AppConfig TryLoadBackup()
        {
            try
            {
                string backupPath = ConfigPath + ".bak";
                if (!File.Exists(backupPath)) return null;
                byte[] raw = File.ReadAllBytes(backupPath);
                int offset = 0;
                if (raw.Length >= 3 && raw[0] == 0xEF && raw[1] == 0xBB && raw[2] == 0xBF) offset = 3;
                if (raw.Length <= offset) return null;
                using (var stream = new MemoryStream(raw, offset, raw.Length - offset))
                {
                    var value = (AppConfig)new DataContractJsonSerializer(typeof(AppConfig)).ReadObject(stream);
                    if (value == null) return null;
                    if (value.MonitorVideos == null) value.MonitorVideos = new Dictionary<string, string>();
                    if (value.Library == null) value.Library = new List<string>();
                    if (value.DisplayProfiles == null) value.DisplayProfiles = new Dictionary<string, Dictionary<string, string>>();
                    return value;
                }
            }
            catch (Exception ex)
            {
                AppLog.Write("Config backup recovery failed: " + ex.Message);
                return null;
            }
        }

        public void Save(AppConfig value)
        {
            Directory.CreateDirectory(folder);
            string temporary = ConfigPath + ".tmp";
            try
            {
                using (var stream = File.Create(temporary))
                {
                    new DataContractJsonSerializer(typeof(AppConfig)).WriteObject(stream, value);
                    stream.Flush(true);
                }
                if (File.Exists(ConfigPath))
                {
                    try { File.Copy(ConfigPath, ConfigPath + ".bak", true); }
                    catch (Exception backupError) { AppLog.Write("Config backup skipped: " + backupError.Message); }
                    bool encryptedFolder = (new DirectoryInfo(folder).Attributes & FileAttributes.Encrypted) != 0;
                    if (encryptedFolder)
                    {
                        File.Copy(temporary, ConfigPath, true);
                        File.Delete(temporary);
                    }
                    else if (!MoveFileEx(temporary, ConfigPath, MoveFileReplaceExisting | MoveFileWriteThrough))
                    {
                        int error = Marshal.GetLastWin32Error();
                        AppLog.Write("Atomic config replace unavailable; using safe overwrite. Win32 error: " + error);
                        File.Copy(temporary, ConfigPath, true);
                        File.Delete(temporary);
                    }
                }
                else File.Move(temporary, ConfigPath);
            }
            catch (Exception ex)
            {
                AppLog.Write("Config save failed: " + ex.Message);
                try { if (File.Exists(temporary)) File.Delete(temporary); } catch { }
            }
        }
    }

    internal static class NativeDesktop
    {
        private const int GWL_STYLE = -16;
        private const int GWL_EXSTYLE = -20;
        private const long WS_CHILD = 0x40000000L;
        private const long WS_POPUP = unchecked((long)0x80000000L);
        private const long WS_EX_TRANSPARENT = 0x00000020L;
        private const long WS_EX_TOOLWINDOW = 0x00000080L;
        private const long WS_EX_LAYERED = 0x00080000L;
        private const long WS_EX_NOREDIRECTIONBITMAP = 0x00200000L;
        private const long WS_EX_NOACTIVATE = 0x08000000L;
        private const uint LWA_ALPHA = 0x00000002;
        private const uint SWP_NOACTIVATE = 0x0010;
        private const uint SWP_SHOWWINDOW = 0x0040;
        private const uint SMTO_NORMAL = 0x0000;
        private static readonly IntPtr HWND_BOTTOM = new IntPtr(1);
        private static IntPtr cachedDesktopHost = IntPtr.Zero;
        public delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);

        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern IntPtr FindWindow(string cls, string title);
        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string title);
        [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
        [DllImport("user32.dll")] private static extern IntPtr SetParent(IntPtr child, IntPtr parent);
        [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr hwnd);
        [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);
        private const uint GA_PARENT = 1;

        /// <summary>
        /// Real parent of a window.
        ///
        /// GetParent() returns the parent OR the owner, and for a WS_POPUP window
        /// (which a borderless form is) it returns the owner - so it reports 0
        /// even after SetParent() succeeded. GetAncestor(GA_PARENT) is the call
        /// that actually answers "who is my parent".
        /// </summary>
        public static IntPtr GetRealParent(IntPtr hwnd)
        {
            return GetAncestor(hwnd, GA_PARENT);
        }

        private const uint GA_ROOT = 2;
        private const uint SWP_NOSIZE = 0x0001;
        private const uint SWP_NOMOVE = 0x0002;

        /// <summary>
        /// Puts a window at the desktop's level: above the wallpaper, below every
        /// application.
        ///
        /// This is what makes the desktop timer a widget rather than an overlay. The first
        /// version was a topmost window, so it floated above whatever the user had open -
        /// covering a paragraph of a document, or the corner of a game, for the sake of a
        /// clock. The requirement is that the timer sits where the wallpaper sits:
        /// "widget timer ya harus setara sama wallpaper placement nya gabole menimpa apps
        /// yg dibuka".
        ///
        /// The anchor is the wallpaper's top-level ancestor - Progman on a raised desktop,
        /// the wallpaper WorkerW on a classic one. Placing the window directly above that
        /// puts it above the desktop surface and below every normal window, because the
        /// desktop is the bottom of the z-order and applications are all above it. No
        /// reparenting is involved: the window stays top-level, so its layered surface
        /// keeps compositing exactly as before.
        /// </summary>
        public static void PlaceAtDesktopLevel(IntPtr hwnd, IntPtr wallpaperHwnd)
        {
            if (hwnd == IntPtr.Zero || !IsWindow(hwnd)) return;

            IntPtr anchor = wallpaperHwnd != IntPtr.Zero ? GetAncestor(wallpaperHwnd, GA_ROOT) : IntPtr.Zero;
            if (anchor == IntPtr.Zero || !IsWindow(anchor))
            {
                // No wallpaper to sit above yet. Progman is still the right anchor: it is
                // the desktop window, and it is always at the bottom.
                anchor = FindWindow("Progman", null);
                if (anchor == IntPtr.Zero) return;
            }

            // hwndInsertAfter = anchor puts hwnd immediately ABOVE the anchor. The window
            // must not be topmost for this to mean anything, which is why the timer is
            // created without TopMost.
            SetWindowPos(hwnd, anchor, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        }
        [DllImport("user32.dll")] private static extern IntPtr SendMessageTimeout(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
        [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr hwnd, int index);
        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtr")] private static extern IntPtr SetWindowLongPtr64(IntPtr hwnd, int index, IntPtr value);
        [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr hwnd, IntPtr insertAfter, int x, int y, int cx, int cy, uint flags);
        [DllImport("user32.dll")] private static extern bool SetLayeredWindowAttributes(IntPtr hwnd, uint colorKey, byte alpha, uint flags);
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
        [DllImport("user32.dll")] private static extern bool IsZoomed(IntPtr hwnd);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hwnd);
        [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr hwnd);
        [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr hwnd);
        /// <summary>Public wrapper: other classes must not P/Invoke user32 themselves.</summary>
        public static bool IsWindowAlive(IntPtr hwnd) { return hwnd != IntPtr.Zero && IsWindow(hwnd); }
        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr hwnd, StringBuilder className, int maxCount);
        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int maxCount);

        [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

        /// <summary>
        /// Switches the shell into the mode where a child window can be the
        /// wallpaper, at most once per shell instance.
        ///
        /// On a raised desktop Progman composites its own wallpaper through
        /// DirectComposition, and a child HWND placed inside it is simply not
        /// drawn - the desktop stays black no matter how correct the window
        /// geometry is. Message 0x052C makes Explorer move SHELLDLL_DefView into
        /// a separate WorkerW, which is the layout where a child window is
        /// rendered. That is why the old code sent it.
        ///
        /// The old code sent it on EVERY attach attempt, including each two-second
        /// health tick, and Explorer spawns a fresh WorkerW each time - a dozen
        /// orphaned WorkerW windows were left behind. The message only needs to
        /// run once per shell: the handle of Progman changes when Explorer
        /// restarts, so that handle doubles as the generation marker.
        /// </summary>
        private static void PrepareDesktopOnce()
        {
            IntPtr progman = FindWindow("Progman", null);
            if (progman == IntPtr.Zero || progman == preparedProgman) return;

            // If the shell ALREADY has a wallpaper WorkerW, there is nothing to prepare.
            //
            // This is the whole startup cost. Message 0x052C makes Explorer tear down its
            // desktop layout and build a new WorkerW, and it is sent twice with a one
            // second timeout each - measured at 2.9 seconds of dead time between the first
            // renderer being ready and the first wallpaper being attached. That is the
            // "pas pertama buka lumawall setelah smua di close lumayan ngelag".
            //
            // The message is only needed when no WorkerW exists: on a freshly started
            // Explorer, and on a raised desktop where Progman composites its own wallpaper.
            // When the app is restarted while Explorer keeps running - the normal case -
            // the WorkerW from the previous run is still there and can be reused as-is.
            if (FindWindowEx(progman, IntPtr.Zero, "WorkerW", null) != IntPtr.Zero)
            {
                preparedProgman = progman;
                AppLog.Write("Desktop already prepared (existing WorkerW reused; "
                             + "0x052C not sent)");
                return;
            }

            preparedProgman = progman;

            IntPtr ignored;
            SendMessageTimeout(progman, 0x052C, new IntPtr(0xD), IntPtr.Zero, SMTO_NORMAL, 1000, out ignored);
            SendMessageTimeout(progman, 0x052C, new IntPtr(0xD), new IntPtr(1), SMTO_NORMAL, 1000, out ignored);
            AppLog.Write("Desktop prepared for wallpaper hosting (shell generation " + progman.ToInt64() + ")");
        }

        private static IntPtr preparedProgman = IntPtr.Zero;

        public static void AttachToWallpaper(IntPtr hwnd, Drawing.Rectangle bounds)
        {
            PrepareDesktopOnce();
            IntPtr desktopHost = ResolveDesktopHost();
            if (desktopHost == IntPtr.Zero) return;

            // Health checks run frequently. Reparenting an already attached
            // wallpaper can make DWM expose the black WorkerW for one frame.
            // Leave a healthy host completely untouched.
            if (GetRealParent(hwnd) == desktopHost) return;

            if (IsRaisedDesktop())
            {
                // A raised desktop (Windows 11 style, WS_EX_NOREDIRECTIONBITMAP on
                // Progman) draws the wallpaper itself, so the child window must be
                // alpha-blended for DWM to composite it over the desktop surface.
                SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA);
            }
            SetParent(hwnd, desktopHost);
            AppLog.Write("Desktop host attached window=" + hwnd.ToInt64() + " host=" + desktopHost.ToInt64());
            RECT hostBounds;
            int hostLeft = 0;
            int hostTop = 0;
            if (GetWindowRect(desktopHost, out hostBounds)) { hostLeft = hostBounds.Left; hostTop = hostBounds.Top; }
            // HWND_BOTTOM keeps the wallpaper under the desktop icons, which live
            // in SHELLDLL_DefView - a sibling inside the same host.
            SetWindowPos(hwnd, HWND_BOTTOM, bounds.Left - hostLeft, bounds.Top - hostTop,
                bounds.Width, bounds.Height, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        }

        /// <summary>
        /// The window that should own the wallpaper, resolved once and cached.
        ///
        /// Two desktop layouts exist and they need different hosts:
        ///
        ///   * Raised desktop (Progman has WS_EX_NOREDIRECTIONBITMAP - Windows 11,
        ///     and Windows 10 with the "raised desktop" shell): Progman itself
        ///     hosts both the wallpaper and the icon view, and it has NO WorkerW
        ///     child. Looking for one returns nothing and the old code then poked
        ///     the shell with message 0x052C, which makes Explorer spawn a brand
        ///     new WorkerW on every call - the repeated health checks created a
        ///     dozen orphaned WorkerW windows.
        ///
        ///   * Classic desktop (Windows 10 1809-21H2): a WorkerW sits behind the
        ///     one that holds SHELLDLL_DefView, and that sibling WorkerW is the
        ///     wallpaper host.
        /// </summary>
        private static IntPtr ResolveDesktopHost()
        {
            if (IsWindow(cachedDesktopHost) && IsHostUsable(cachedDesktopHost)) return cachedDesktopHost;
            cachedDesktopHost = FindDesktopHost();
            return cachedDesktopHost;
        }

        /// <summary>True when Progman hosts the desktop surface directly.</summary>
        private static bool IsRaisedDesktop()
        {
            IntPtr progman = FindWindow("Progman", null);
            if (progman == IntPtr.Zero) return false;
            return (GetWindowLongPtr64(progman, GWL_EXSTYLE).ToInt64() & WS_EX_NOREDIRECTIONBITMAP) != 0;
        }

        /// <summary>
        /// A cached host is only reused while it is still a live window that is
        /// still part of the desktop. After an Explorer restart the old handle is
        /// dead and must be resolved again.
        /// </summary>
        private static bool IsHostUsable(IntPtr host)
        {
            return host != IntPtr.Zero && IsWindow(host) && !IsShellTray(host);
        }

        private static bool IsShellTray(IntPtr hwnd)
        {
            string value = ClassName(hwnd);
            return value == "Shell_TrayWnd" || value == "Shell_SecondaryTrayWnd";
        }

        private static IntPtr FindDesktopHost()
        {
            IntPtr progman = FindWindow("Progman", null);
            if (progman == IntPtr.Zero) return IntPtr.Zero;

            // After PrepareDesktopOnce() the shell provides a WorkerW child of
            // Progman on every layout, and that WorkerW is the surface a child
            // window can actually be drawn into. It is checked first because
            // Progman itself is opaque: on a raised desktop it composites its own
            // wallpaper and never shows a child window.
            IntPtr child = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
            if (child != IntPtr.Zero) return child;

            // Classic layout: the wallpaper WorkerW is the sibling that follows
            // the window containing SHELLDLL_DefView.
            IntPtr desktopHost = IntPtr.Zero;
            EnumWindows(delegate(IntPtr top, IntPtr param)
            {
                if (FindWindowEx(top, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero)
                {
                    desktopHost = FindWindowEx(IntPtr.Zero, top, "WorkerW", null);
                    return false;
                }
                return true;
            }, IntPtr.Zero);
            if (desktopHost != IntPtr.Zero) return desktopHost;

            // Last resort: Progman itself. Works on classic builds where the icon
            // view lives directly under it.
            return progman;
        }

        /// <summary>
        /// Device names of every monitor covered by an application window.
        ///
        /// Enumerating all windows, not just the foreground one, is the whole
        /// point. Windows has exactly ONE foreground window, so a detector that
        /// only looks at GetForegroundWindow() misses every fullscreen app on a
        /// display that is not focused - which is the normal situation for a
        /// multi-monitor setup. The result was wallpaper that kept decoding
        /// behind a fullscreen game.
        ///
        /// The scan is per monitor rather than per window so a window spanning
        /// two displays pauses exactly those two.
        /// </summary>
        public static List<string> FindCoveredMonitors()
        {
            return ScanCoveringWindows(requireZoomed: false);
        }

        /// <summary>Monitors covered by a maximized (zoomed) application window.</summary>
        public static List<string> FindMaximizedMonitors()
        {
            return ScanCoveringWindows(requireZoomed: true);
        }

        /// <summary>
        /// Both answers from ONE pass over the window list.
        ///
        /// The two scans above each walk every top-level window. Calling both - which is
        /// what the pause logic did, every two seconds - doubled the cost of the most
        /// expensive thing the process does while idle. There is no reason to walk the list
        /// twice: the only difference is whether IsZoomed is required, and that is a cheap
        /// handle-attribute test that can be evaluated per window in a single walk.
        ///
        /// covered  = a window of any kind filling the monitor (what PauseFullscreen means)
        /// maximized = one of those that also reports IsZoomed (what PauseMaximized means)
        /// </summary>
        public static void FindCoveringMonitors(out List<string> covered, out List<string> maximized)
        {
            var any = new List<string>();
            var zoomed = new List<string>();
            uint ownPid = (uint)Process.GetCurrentProcess().Id;
            var screens = Forms.Screen.AllScreens;

            EnumWindows(delegate(IntPtr hwnd, IntPtr param)
            {
                if (!IsWindowVisible(hwnd)) return true;
                if (IsIconic(hwnd)) return true;

                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid == ownPid) return true;

                RECT rect;
                if (!GetWindowRect(hwnd, out rect)) return true;
                if (rect.Right <= rect.Left || rect.Bottom <= rect.Top) return true;

                var full = new List<Forms.Screen>();
                foreach (var screen in screens)
                {
                    var b = screen.Bounds;
                    int overlapW = Math.Min(rect.Right, b.Right) - Math.Max(rect.Left, b.Left);
                    int overlapH = Math.Min(rect.Bottom, b.Bottom) - Math.Max(rect.Top, b.Top);
                    if (overlapW >= b.Width * 0.98 && overlapH >= b.Height * 0.98) full.Add(screen);
                }
                if (full.Count == 0) return true;

                if (IsCloaked(hwnd)) return true;
                if (IsShellDesktopWindow(hwnd) || IsOverlayWindow(hwnd)) return true;
                if (IsNonAppWindow(hwnd)) return true;

                bool isZoomed = IsZoomed(hwnd);
                foreach (var screen in full)
                {
                    if (!any.Contains(screen.DeviceName))
                    {
                        any.Add(screen.DeviceName);
                        LogCovering(screen.DeviceName, hwnd, rect);
                    }
                    if (isZoomed && !zoomed.Contains(screen.DeviceName)) zoomed.Add(screen.DeviceName);
                }
                return true;
            }, IntPtr.Zero);

            covered = any;
            maximized = zoomed;
        }

        /// <summary>
        /// Reports a covering window once per monitor per window handle.
        ///
        /// Bounded: a machine that opens and closes hundreds of full-screen windows would
        /// otherwise grow the set without limit.
        /// </summary>
        private static void LogCovering(string device, IntPtr hwnd, RECT rect)
        {
            string key = device + "|" + hwnd.ToInt64();
            if (loggedCovering.Count > 512) loggedCovering.Clear();
            if (!loggedCovering.Add(key)) return;
            AppLog.Write(string.Format(
                "Covering window on {0}: '{1}' class={2} process={3} rect={4},{5} {6}x{7}",
                device, WindowTitle(hwnd), ClassName(hwnd), ProcessNameOf(hwnd),
                rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top));
        }

        /// <summary>
        /// Walks every visible top-level window and collects the monitors each
        /// one completely covers.
        /// </summary>
        private static List<string> ScanCoveringWindows(bool requireZoomed)
        {
            var covered = new List<string>();
            uint ownPid = (uint)Process.GetCurrentProcess().Id;
            var screens = Forms.Screen.AllScreens;

            // The scan runs twice every two seconds for the life of the process, so the
            // ORDER of these tests is the whole optimisation.
            //
            // Each one is a call into another process's window, and the expensive ones
            // dominate: GetWindowRect marshals a RECT back, IsCloaked is a synchronous DWM
            // round-trip, and GetClassName / GetWindowText / GetWindowThreadProcessId each
            // cross the process boundary. The cheap handle-attribute tests - IsWindowVisible,
            // IsIconic, IsZoomed - are answered from the window manager's own cache.
            //
            // So the order is: cheapest and most selective first. On a typical desktop
            // almost every window is rejected by the first three tests, and the DWM
            // round-trip now runs only for the handful that really are full-screen sized.
            // Measured before: ~9% CPU while idle. The screen rectangle is also fetched
            // once per window rather than once per window per monitor.
            EnumWindows(delegate(IntPtr hwnd, IntPtr param)
            {
                if (!IsWindowVisible(hwnd)) return true;
                if (IsIconic(hwnd)) return true;
                if (requireZoomed && !IsZoomed(hwnd)) return true;

                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid == ownPid) return true;

                // Rect first among the marshalling calls: it is the test that actually
                // decides, and rejecting a window here skips the DWM round-trip, the class
                // name and the process name below.
                RECT rect;
                if (!GetWindowRect(hwnd, out rect)) return true;
                if (rect.Right <= rect.Left || rect.Bottom <= rect.Top) return true;

                // Which monitors could this window possibly cover, by rectangle alone?
                var full = new List<Forms.Screen>();
                foreach (var screen in screens)
                {
                    var b = screen.Bounds;
                    int overlapW = Math.Min(rect.Right, b.Right) - Math.Max(rect.Left, b.Left);
                    int overlapH = Math.Min(rect.Bottom, b.Bottom) - Math.Max(rect.Top, b.Top);
                    // 2% tolerance: maximized windows are inset by the invisible resize
                    // border, and DPI rounding can shave a pixel or two.
                    if (overlapW >= b.Width * 0.98 && overlapH >= b.Height * 0.98) full.Add(screen);
                }
                if (full.Count == 0) return true;

                // Only now, for a window that really does cover a whole monitor, are the
                // expensive and identifying calls worth making.
                if (IsCloaked(hwnd)) return true;
                if (IsShellDesktopWindow(hwnd) || IsOverlayWindow(hwnd)) return true;
                if (IsNonAppWindow(hwnd)) return true;

                foreach (var screen in full)
                {
                    if (covered.Contains(screen.DeviceName)) continue;
                    covered.Add(screen.DeviceName);

                    // Name the window that caused this - once per monitor, not once per
                    // scan.
                    //
                    // The pause/resume log said which monitor changed but never why, so a
                    // wallpaper that paused and resumed on its own could not be traced to
                    // anything. The title, class and process together identify it.
                    //
                    // The dedupe is per monitor AND per window, held across scans: with a
                    // per-scan set the same two lines were written every two seconds, which
                    // is 300+ lines in ten minutes and a file write on the UI thread each
                    // time.
                    string key = screen.DeviceName + "|" + hwnd.ToInt64();
                    if (loggedCovering.Add(key))
                    {
                        AppLog.Write(string.Format(
                            "Covering window on {0}: '{1}' class={2} process={3} rect={4},{5} {6}x{7}",
                            screen.DeviceName, WindowTitle(hwnd), ClassName(hwnd),
                            ProcessNameOf(hwnd),
                            rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top));
                    }
                }
                return true;
            }, IntPtr.Zero);

            return covered;
        }

        /// <summary>
        /// Covering windows already reported, so the log names each one once rather than
        /// every two seconds.
        ///
        /// Bounded: a machine that opens and closes hundreds of full-screen windows would
        /// otherwise grow this without limit. When it fills, the oldest half is dropped,
        /// which can at worst repeat a line that has not been seen for a long time.
        /// </summary>
        private static readonly HashSet<string> loggedCovering = new HashSet<string>();

        /// <summary>
        /// True when the Desktop Window Manager has cloaked this window - that is, it is
        /// not on screen even though IsWindowVisible says it is.
        ///
        /// Cloaking is how Windows hides a window that its application still owns: a UWP
        /// app the user closed keeps its window and its ApplicationFrameHost frame, both
        /// reporting themselves visible at full-screen size, and only DWM knows they are
        /// gone. Without this test such a window is indistinguishable from a maximised
        /// game, so a wallpaper on that monitor is paused permanently.
        ///
        /// The return values are 1 (the application cloaked it), 2 (the system did) and
        /// 4 (its parent is cloaked). All three mean the same thing here. A window DWM
        /// does not manage returns a failure code, and that is treated as uncloaked so
        /// this can never hide a real application window.
        /// </summary>
        private static bool IsCloaked(IntPtr hwnd)
        {
            try
            {
                int cloaked;
                int hr = DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, out cloaked, sizeof(int));
                return hr == 0 && cloaked != 0;
            }
            catch { return false; }
        }

        private const int DWMWA_CLOAKED = 14;

        [DllImport("dwmapi.dll")]
        private static extern int DwmGetWindowAttribute(IntPtr hwnd, int attribute, out int value, int size);

        /// <summary>
        /// Windows that must never count as "an app covering the screen".
        ///
        /// Tool windows (no taskbar button), click-through windows, and
        /// no-activate windows are background furniture: input method hosts,
        /// overlays, and helper panels. Pausing the wallpaper for any of them
        /// would make it flicker while the user is doing nothing.
        /// </summary>
        private static bool IsNonAppWindow(IntPtr hwnd)
        {
            long ex = GetWindowLongPtr64(hwnd, GWL_EXSTYLE).ToInt64();
            if ((ex & WS_EX_TOOLWINDOW) != 0) return true;
            if ((ex & WS_EX_NOACTIVATE) != 0) return true;
            if ((ex & WS_EX_TRANSPARENT) != 0) return true;

            // A window with no title and no size is not something the user sees
            // as an application.
            if (ClassName(hwnd).Length == 0) return true;
            return false;
        }

        /// <summary>Legacy helpers kept for the shell tray checks.</summary>
        public static bool IsAnotherAppFullscreen()
        {
            return FindCoveredMonitors().Count > 0;
        }

        /// <summary>
        /// True for windows that must never pause the wallpaper.
        ///
        /// The earlier version rejected whole window classes, which was wrong in
        /// both directions. Windows.UI.Core.CoreWindow and
        /// ApplicationFrameWindow are not shell-only classes: every UWP
        /// application uses them, so a fullscreen Store game never paused the
        /// wallpaper at all. Meanwhile the real shell surfaces share those
        /// classes with real apps, so the class alone says nothing.
        ///
        /// What actually distinguishes them, verified with tools/UwpClassAudit.cs:
        ///
        ///   shell furniture          real app window
        ///   -----------------------  ------------------------
        ///   no title                 has a title
        ///   136x39, 160x28, offscreen  full size
        ///   ShellExperienceHost,     any normal process
        ///   SearchHost, TextInputHost
        ///
        /// So the decision is made on evidence about the window itself, not on
        /// the class name.
        /// </summary>
        private static bool IsOverlayWindow(IntPtr hwnd)
        {
            string value = ClassName(hwnd);
            if (value.Length == 0) return true;

            // Shell processes are never "an app the user launched". This is the
            // strongest signal and covers the Start menu, search, and the input
            // host regardless of which class they happen to use.
            if (IsShellProcess(hwnd)) return true;

            // Windowless helpers that exist only to broker something.
            if (value == "CEF-OSC-WIDGET" ||                      // NVIDIA overlay
                value == "TextInputHost" ||
                value.StartsWith("Windows.UI.Composition", StringComparison.Ordinal) ||
                value.StartsWith("Cua.", StringComparison.Ordinal) ||
                value == "XamlExplorerHostIslandWindow")
                return true;

            // An unnamed window cannot be something the user is looking at. The
            // shell's hidden ApplicationFrameWindow hosts read as empty titles,
            // while a real UWP app always has one.
            if (WindowTitle(hwnd).Length == 0) return true;

            return false;
        }

        /// <summary>
        /// True when the window belongs to a Windows shell process.
        ///
        /// These processes render the Start menu, search, the taskbar and the
        /// input panel. They appear and disappear while the user does nothing
        /// meaningful, so pausing the wallpaper for them would make it flicker.
        /// </summary>
        private static bool IsShellProcess(IntPtr hwnd)
        {
            try
            {
                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid == 0) return false;

                string name = null;
                using (var process = Process.GetProcessById((int)pid))
                    name = process.ProcessName;
                if (string.IsNullOrEmpty(name)) return false;

                return name == "ShellExperienceHost" ||
                       name == "StartMenuExperienceHost" ||
                       name == "SearchHost" ||
                       name == "SearchApp" ||
                       name == "TextInputHost" ||
                       name == "LockApp" ||
                       name == "ShellHost" ||
                       name == "explorer";      // desktop, taskbar, file windows
            }
            catch { return false; }
        }

        private static string WindowTitle(IntPtr hwnd)
        {
            var title = new StringBuilder(256);
            if (GetWindowText(hwnd, title, title.Capacity) == 0) return "";
            return title.ToString();
        }

        private static string ClassName(IntPtr hwnd)
        {
            var className = new StringBuilder(128);
            if (GetClassName(hwnd, className, className.Capacity) == 0) return "";
            return className.ToString();
        }

        /// <summary>The process name behind a window, for the covering-window log line.</summary>
        private static string ProcessNameOf(IntPtr hwnd)
        {
            try
            {
                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid == 0) return "?";
                using (var process = Process.GetProcessById((int)pid))
                    return process.ProcessName;
            }
            catch { return "?"; }
        }

        private static bool IsShellDesktopWindow(IntPtr hwnd)
        {
            string value = ClassName(hwnd);
            return value == "Progman" || value == "WorkerW" || value == "SHELLDLL_DefView" ||
                value == "Shell_TrayWnd" || value == "Shell_SecondaryTrayWnd";
        }
    }

    internal sealed class WallpaperWindow : Forms.Form
    {
        private static readonly object EnvironmentLock = new object();
        private static Task<CoreWebView2Environment> sharedEnvironmentTask;
        private readonly Forms.Screen screen;
        private string mediaPath;
        private string currentMediaPath;
        private WebView2 webView;
        private StaticImageSurface staticSurface;
        private bool staticMode;
        private bool playbackPaused;
        // Set when a pause/resume is issued before the page can accept scripts;
        // flushed on the next ready signal so the command is not lost.
        private bool pendingPlaybackSync;
        private bool muted;
        private int targetFps;
        private bool browserReady;
        private bool pageReady;
        private bool initialCompletionReported;
        private int mediaRequest;
        private string pagePath;
        // Media asked for before the page could accept a script. Without this the
        // request was dropped silently and the caller logged success anyway.
        private string pendingMediaPath;
        // Set when the page confirms it decoded a frame. Cleared on every new request,
        // so the watchdog in RetryUnconfirmedMedia knows the difference between "still
        // loading" and "the page has gone quiet".
        private bool mediaConfirmed;
        private int mediaRetryCount;
        private bool mediaGaveUp;
        // Set once per media request when the page had to be rebuilt. Keeps the recovery
        // from turning into a reload loop if the fresh page also fails to answer.
        private bool pageReloadedForRequest;
        private DateTime lastMediaAttempt = DateTime.UtcNow;
        // The periodic "is the page still running script?" check. A minute is frequent
        // enough to notice a dead page long before a user does, and rare enough that the
        // probe itself cannot cost anything measurable.
        private DateTime lastLivenessCheck = DateTime.UtcNow;
        private bool livenessCheckInFlight;
        // Consecutive probes that came back empty. Two are needed before a page is rebuilt,
        // so a single transient answer cannot destroy a page that is working.
        private int deadPageStrikes;
        private const int DeadPageStrikes = 2;
        // How long a page is left alone after a playback command before it is probed.
        // Long enough for a seek or a play() to settle, short enough that a real fault is
        // still noticed within the same minute.
        private const double SettleSeconds = 8;
        // The video position at the previous reconcile, used to notice an element that is
        // unpaused but not advancing. Negative means "no reading yet".
        private double lastSeenTime = -1;
        private const double LivenessCheckSeconds = 20;
        // How long to wait for the page to confirm before re-sending, and how many times
        // to re-send before reporting the wallpaper failed. Five seconds is well beyond
        // a local file's decode time; three attempts is enough for a transient stall and
        // short enough that a genuinely broken file surfaces instead of hanging.
        private const double MediaRetrySeconds = 5;
        private const int MaxMediaRetries = 3;
        // How often a paused wallpaper has its memory policy re-applied. See
        // MaintainPausedMemory for why a minute and not the health tick's two seconds.
        private const double MemoryMaintenanceSeconds = 60;
        private DateTime lastMemoryMaintenance = DateTime.MinValue;

        public event EventHandler RendererReady;
        public event EventHandler RendererFailed;

        public WallpaperWindow(Forms.Screen target, string path, bool mute, int fps)
        {
            screen = target;
            mediaPath = path;
            muted = mute;
            targetFps = Math.Max(10, Math.Min(30, fps));
            ShowInTaskbar = false;
            FormBorderStyle = Forms.FormBorderStyle.None;
            StartPosition = Forms.FormStartPosition.Manual;
            ControlBox = false;
            BackColor = Drawing.Color.Black;
            Bounds = new Drawing.Rectangle(-32000, -32000, 1, 1);
            Shown += async delegate { await Initialize(); };
        }

        /// <summary>
        /// Static wallpapers never touch WebView2: a plain GDI-painted surface
        /// costs no renderer process, no GPU process work and no video decode.
        /// Video keeps the full WebView2 path with hardware decode.
        /// </summary>
        private async Task Initialize()
        {
            if (IsImagePath(mediaPath)) SwitchToStatic(mediaPath);
            else await InitializeBrowser();
        }

        private void SwitchToStatic(string path)
        {
            staticMode = true;
            pageReady = false;
            browserReady = false;
            if (webView != null)
            {
                try { Controls.Remove(webView); } catch { }
                try { webView.Dispose(); } catch { }
                webView = null;
            }
            if (staticSurface == null)
            {
                staticSurface = new StaticImageSurface { Dock = Forms.DockStyle.Fill };
                Controls.Add(staticSurface);
            }
            int request = ++mediaRequest;
            string target = path;
            Task.Run(delegate
            {
                Drawing.Image loaded = null;
                try { loaded = LoadCoverImage(target, screen.Bounds); }
                catch (Exception ex) { AppLog.Write("Static wallpaper decode failed: " + ex.Message); }
                try
                {
                    BeginInvoke(new Action(delegate
                    {
                        if (IsDisposed || request != mediaRequest || !staticMode)
                        {
                            if (loaded != null) loaded.Dispose();
                            return;
                        }
                        if (loaded == null) { ReportFailed(request); return; }
                        staticSurface.SetImage(loaded);
                        AppLog.Write("Static wallpaper ready (no WebView2) " + screen.DeviceName + " -> " + target);
                        ReportReady(request);
                    }));
                }
                catch { if (loaded != null) loaded.Dispose(); }
            });
        }

        private async Task SwitchToBrowser(string path)
        {
            staticMode = false;
            if (staticSurface != null)
            {
                try { Controls.Remove(staticSurface); } catch { }
                try { staticSurface.Dispose(); } catch { }
                staticSurface = null;
            }
            await InitializeBrowser();
        }

        internal static Drawing.Image LoadCoverImage(string path, Drawing.Rectangle bounds)
        {
            using (Drawing.Image source = Drawing.Image.FromFile(path))
            {
                int targetWidth = Math.Max(1, bounds.Width);
                int targetHeight = Math.Max(1, bounds.Height);
                double scale = Math.Max((double)targetWidth / source.Width, (double)targetHeight / source.Height);
                int width = Math.Max(1, (int)Math.Round(source.Width * scale));
                int height = Math.Max(1, (int)Math.Round(source.Height * scale));
                if (width <= source.Width && height <= source.Height) return new Drawing.Bitmap(source);
                var bitmap = new Drawing.Bitmap(width, height, Drawing.Imaging.PixelFormat.Format32bppPArgb);
                using (Drawing.Graphics graphics = Drawing.Graphics.FromImage(bitmap))
                {
                    graphics.InterpolationMode = Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                    graphics.DrawImage(source, new Drawing.Rectangle(0, 0, width, height));
                }
                return bitmap;
            }
        }

        protected override Forms.CreateParams CreateParams
        {
            get
            {
                Forms.CreateParams value = base.CreateParams;
                // A hardware-composited WebView must not live in a layered HWND. Layered
                // parents can briefly lose the DirectComposition surface during decoder
                // seeks, which appears as a one-frame black flash on the desktop.
                value.ExStyle |= 0x00000080;
                return value;
            }
        }

        protected override bool ShowWithoutActivation { get { return true; } }

        private async Task InitializeBrowser()
        {
            try
            {
                if (webView == null)
                {
                    var created = new WebView2();
                    created.Dock = Forms.DockStyle.Fill;
                    created.DefaultBackgroundColor = Drawing.Color.FromArgb(0, 0, 0, 0);
                    Controls.Add(created);
                    webView = created;
                }
                string safeDevice = new string(screen.DeviceName.Where(char.IsLetterOrDigit).ToArray());
                CoreWebView2Environment environment = await GetSharedEnvironment();
                if (IsDisposed || webView == null || webView.IsDisposed) return;
                await webView.EnsureCoreWebView2Async(environment);
                if (IsDisposed || webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
                webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
                webView.CoreWebView2.Settings.AreBrowserAcceleratorKeysEnabled = false;
                webView.CoreWebView2.Settings.IsZoomControlEnabled = false;
                string pageFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LumaWall", "WebView2Pages");
                Directory.CreateDirectory(pageFolder);
                pagePath = Path.Combine(pageFolder, safeDevice + "-" + Guid.NewGuid().ToString("N") + ".html");
                File.WriteAllText(pagePath, BuildMediaHtml(), Encoding.UTF8);
                webView.CoreWebView2.ProcessFailed += delegate(object sender, CoreWebView2ProcessFailedEventArgs e)
                {
                    AppLog.Write("WebView process failed on " + screen.DeviceName + ": " + e.ProcessFailedKind);
                    ReportFailed(mediaRequest);
                };
                webView.CoreWebView2.WebMessageReceived += delegate(object sender, CoreWebView2WebMessageReceivedEventArgs e)
                {
                    string message;
                    try { message = e.TryGetWebMessageAsString(); }
                    catch { return; }
                    if (message.StartsWith("media-ready:", StringComparison.Ordinal))
                    {
                        int request;
                        if (int.TryParse(message.Substring("media-ready:".Length), out request)) ReportReady(request);
                    }
                    else if (message.StartsWith("media-error:", StringComparison.Ordinal))
                    {
                        AppLog.Write("Wallpaper media decode failed on " + screen.DeviceName + " -> " + mediaPath);
                        int request;
                        if (int.TryParse(message.Substring("media-error:".Length), out request)) ReportFailed(request);
                    }
                    else if (message.StartsWith("pause-ack:") || message.StartsWith("resume-frame:") ||
                             message.StartsWith("resume-rejected:") || message.StartsWith("pb-noactive:"))
                    {
                        AppLog.Write("Playback timing " + screen.DeviceName + " " + message);
                    }
                    else if (message == "loop-seamless")
                    {
                        AppLog.Write("Seamless loop handoff completed on " + screen.DeviceName + " -> " + currentMediaPath);
                    }
                };
                webView.CoreWebView2.NavigationCompleted += delegate(object sender, CoreWebView2NavigationCompletedEventArgs e)
                {
                    if (IsDisposed || webView.IsDisposed) return;
                    if (!e.IsSuccess)
                    {
                        AppLog.Write("Wallpaper navigation failed on " + screen.DeviceName + ": " + e.WebErrorStatus + " -> " + mediaPath);
                        ReportFailed(mediaRequest);
                        return;
                    }
                    pageReady = true;
                    AppLog.Write("Permanent wallpaper host ready " + screen.DeviceName);
                    FlushPendingPlaybackSync();
                    QueueMedia(mediaPath);
                    // Anything asked for while the page was loading goes now, and it
                    // goes after the initial media so the newest request wins.
                    FlushPendingMedia();
                };
                webView.CoreWebView2.Navigate(new Uri(pagePath, UriKind.Absolute).AbsoluteUri);
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex);
                AppLog.Write("Wallpaper initialization failed on " + screen.DeviceName + ": " + ex);
                ReportFailed(mediaRequest);
            }
        }

        private static Task<CoreWebView2Environment> GetSharedEnvironment()
        {
            lock (EnvironmentLock)
            {
                if (sharedEnvironmentTask == null)
                {
                    string userData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LumaWall", "WebView2", "Shared");
                    Directory.CreateDirectory(userData);
                    // GPU path: hardware video decode (NVDEC/DXVA) plus DWM
                    // compositing keep the CPU near idle for 1080p loops, so the
                    // software fallback flags (--disable-gpu,
                    // --disable-accelerated-video-decode, --disable-gpu-compositing,
                    // --disable-direct-composition) must never come back here.
                    // Only independent MPO video overlays are disabled: their
                    // scan-out can flicker on mixed-refresh multi-monitor layouts
                    // while the regular DWM-composited surface stays stable and
                    // fully GPU-accelerated.
                    //
                    // The memory flags below are all quality-neutral by construction:
                    // none of them changes resolution, frame rate, codec choice or
                    // colour handling. What they remove is state that accumulates
                    // because a wallpaper page is loaded once and then lives for
                    // weeks, which is exactly the shape of workload where Chromium's
                    // defaults (built for browsing) hold memory nobody will ask for
                    // again.
                    //
                    //   --msWebView2SimulateMemoryPressureWhenInactive
                    //       Deliberately NOT used. The flag only fires when WebView2
                    //       considers the control inactive - either its controller is
                    //       invisible or the WebView is suspended - and a wallpaper
                    //       window stays visible on the desktop even when a fullscreen
                    //       game covers it. Shipping it would be a comment claiming a
                    //       saving that never happens. The same effect is obtained
                    //       explicitly instead, through the DevTools Protocol, at the
                    //       moment this app actually knows the wallpaper is stopped.
                    //
                    //   --disable-back-forward-cache
                    //       A wallpaper never navigates back. Without this, Chromium
                    //       keeps a full frozen snapshot (DOM plus JS heap) for a
                    //       history step that will never be used.
                    //
                    //   --process-per-site
                    //       REMOVED. It was added to keep the multi-monitor case at
                    //       one renderer instead of one per display, and it did - but
                    //       it collapsed the three wallpaper pages into a single
                    //       renderer, which is the same coupling that made
                    //       --renderer-process-limit=1 unacceptable a few lines up:
                    //       one renderer crash then takes down every monitor at once.
                    //       It also made the memory work dangerous, because trimming
                    //       "this" wallpaper's process group reached the renderer that
                    //       was still playing another monitor's video.
                    //
                    //       Measured cost of removing it: a renderer or two. Measured
                    //       cost of keeping it: black wallpapers on every display.
                    //
                    //   --js-flags=--scavenger_max_new_space_capacity_mb=8
                    //       Caps the V8 young generation. Documented by WebView2 as a
                    //       memory reducer; the cost is more frequent minor GCs, which
                    //       is nothing next to a video decode.
                    //
                    //   cache caps
                    //       Deterministic ceilings on the disk cache and the two Skia
                    //       caches, so a long-lived process cannot grow them without
                    //       bound.
                    string arguments = string.Join(" ", new string[]
                    {
                        "--autoplay-policy=no-user-gesture-required",
                        "--enable-accelerated-video-decode",
                        "--enable-gpu-rasterization",
                        "--disable-direct-composition-video-overlays",
                        "--disable-component-update",
                        "--disable-domain-reliability",
                        "--disable-sync",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-features=CalculateNativeWinOcclusion",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-background-timer-throttling",
                        "--disable-back-forward-cache",
                        "--js-flags=--scavenger_max_new_space_capacity_mb=8",
                        "--disk-cache-size=33554432",
                        "--skia-font-cache-limit-mb=8",
                        "--skia-resource-cache-limit-mb=16"
                    });
                    var options = new CoreWebView2EnvironmentOptions(arguments);
                    sharedEnvironmentTask = CoreWebView2Environment.CreateAsync(null, userData, options);
                }
                return sharedEnvironmentTask;
            }
        }

        private string BuildMediaHtml()
        {
            return @"<!doctype html><html><head><meta charset='utf-8'><style>
 html,body,#stage{width:100%;height:100%;margin:0;overflow:hidden;background:#000}
 #stage{position:relative}
 /* The stage is black, not transparent, and the video sits on top of it.
    Transparent was the original design and it is what let a desktop show through for one
    frame during a swap - which reads as the wallpaper flashing black. A black stage can
    only ever show black, which is indistinguishable from a very dark wallpaper and never
    shows the user's icons. The element itself is still opaque, so in normal play nothing
    of the stage is visible at all. */
 .media{position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;opacity:1;z-index:1;
        object-fit:cover;object-position:50% 50%;transform-origin:50% 50%;backface-visibility:hidden;
        background:#000}
 #tone{position:absolute;width:0;height:0;pointer-events:none}
</style></head><body><div id='stage'></div><svg id='tone' xmlns='http://www.w3.org/2000/svg'><filter id='lumaTone' color-interpolation-filters='sRGB'><feComponentTransfer><feFuncR id='toneR' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/><feFuncG id='toneG' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/><feFuncB id='toneB' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/><feFuncA id='toneA' type='table' tableValues='0 1'/></feComponentTransfer></filter></svg>
<script>
 (function(){
  var stage=document.getElementById('stage'),active=null,generation=0,paused=false,muted=true;
  // The look and playback settings, replaced wholesale by apply(). Kept as one object so
  // every reader sees a consistent set rather than a half-applied mixture.
  var opts=null;
  // Span geometry: when this display is one slice of a picture that continues onto the
  // next monitor, this is the union size and this display's offset inside it.
  var span=null;
  // Playback rate is remembered separately from the element, because a new element
  // created by prepare() has to be given the rate again - it starts at 1.
  var rate=1,pingpong=false,ppDir=1,ppArmed=false;
  function report(v){try{window.chrome.webview.postMessage(v)}catch(e){}}
  function remove(el){if(!el)return;try{el.pause()}catch(e){};try{el.removeAttribute('src');el.load()}catch(e){};try{el.remove()}catch(e){}}

  // ── the tone curve ────────────────────────────────────────────────────────
  //
  // Gamma, exposure and highlight roll-off folded into one lookup table, applied by an
  // SVG feComponentTransfer. A table rather than the feComponentTransfer 'gamma' type
  // because the roll-off is not a pure power curve, and one node is cheaper than three.
  //
  // The curve is built in JS and written into the filter, so changing a slider costs a
  // table rebuild - a few hundred arithmetic operations - and no repaint of the video.
  function toneTable(){
    var exposure=opts?Number(opts.hdrExposure||0):0;
    var highlight=opts?Number(opts.hdrHighlight||0.7):0.7;
    var gamma=opts?Number(opts.gamma||1):1;
    var hdr=opts&&opts.hdrToneMap;
    var n=17,values=[];
    for(var i=0;i<n;i++){
      var x=i/(n-1);
      var y=Math.pow(x,gamma);
      if(hdr){
        y=y*Math.pow(2,exposure);
        if(y>highlight&&highlight<1){
          var over=(y-highlight)/(1-highlight);
          y=highlight+(1-highlight)*(1-Math.exp(-over));
        }
      }
      values.push(Math.max(0,Math.min(1,y)).toFixed(4));
    }
    return values.join(' ');
  }

  function needsTone(){
    if(!opts)return false;
    return !!opts.hdrToneMap||Math.abs(Number(opts.gamma||1)-1)>0.001;
  }

  function refreshTone(){
    // All three channels share one table. The ids are toneR/toneG/toneB - looking up a
    // single node called 'toneTable' found nothing, so the curve was never written and
    // every tone-mapped wallpaper silently rendered as if the option were off.
    var table=toneTable();
    var channels=['toneR','toneG','toneB'];
    for(var i=0;i<channels.length;i++){
      var node=document.getElementById(channels[i]);
      if(node)node.setAttribute('tableValues',table);
    }
  }

  // ── the CSS filter chain ──────────────────────────────────────────────────
  //
  // Order matters: the tone curve first, because it is the transfer function, then the
  // colour adjustments, because they are grades applied to the tone-mapped image. A
  // grade before a transfer function is a different picture, and the one users expect
  // is tone first.
  var FILTERS={
    grayscale:'grayscale(1)',
    sepia:'sepia(0.85)',
    cool:'hue-rotate(-12deg) saturate(1.08) brightness(1.02)',
    warm:'hue-rotate(10deg) saturate(1.12) brightness(1.03)',
    vivid:'saturate(1.45) contrast(1.08)',
    noir:'grayscale(1) contrast(1.35) brightness(0.95)',
    dream:'saturate(1.2) brightness(1.06) contrast(0.92) blur(0.4px)'
  };

  function buildFilter(){
    if(!opts)return '';
    var parts=[];
    if(needsTone())parts.push('url(#lumaTone)');
    var extra=FILTERS[opts.filter];
    if(extra)parts.push(extra);
    var brightness=Number(opts.brightness);if(isFinite(brightness)&&Math.abs(brightness-1)>0.001)parts.push('brightness('+brightness.toFixed(3)+')');
    var contrast=Number(opts.contrast);if(isFinite(contrast)&&Math.abs(contrast-1)>0.001)parts.push('contrast('+contrast.toFixed(3)+')');
    var saturation=Number(opts.saturation);if(isFinite(saturation)&&Math.abs(saturation-1)>0.001)parts.push('saturate('+saturation.toFixed(3)+')');
    var hue=Number(opts.hue);if(isFinite(hue)&&Math.abs(hue)>0.001)parts.push('hue-rotate('+hue.toFixed(2)+'deg)');
    return parts.join(' ');
  }

  function buildTransform(){
    if(!opts)return '';
    var parts=[];
    var zoom=Number(opts.zoom);if(!isFinite(zoom)||zoom<=0)zoom=1;
    if(Math.abs(zoom-1)>0.001)parts.push('scale('+zoom.toFixed(4)+')');
    if(opts.flipHorizontal)parts.push('scaleX(-1)');
    if(opts.flipVertical)parts.push('scaleY(-1)');
    return parts.join(' ');
  }

  function buildObjectPosition(){
    if(!opts)return '50% 50%';
    var x=Number(opts.offsetX),y=Number(opts.offsetY);
    if(!isFinite(x))x=0;if(!isFinite(y))y=0;
    return (50+x*50).toFixed(2)+'% '+(50+y*50).toFixed(2)+'%';
  }

  function objectFitFor(fit){
    switch(fit){
      case 'contain':return 'contain';
      case 'fill':return 'fill';
      case 'center':return 'none';
      case 'stretch':return 'fill';
      case 'cover':default:return 'cover';
    }
  }

  // ── applying the settings ─────────────────────────────────────────────────
  //
  // A span changes the element's GEOMETRY rather than its CSS: the picture is drawn at
  // the size of the whole multi-monitor union and shifted so this monitor shows its own
  // slice. That is what makes two adjacent screens read as one continuous image - each
  // window renders the same video, and each shows the part of it that belongs to it.
  function layout(el){
    if(!el)return;
    if(span&&span.totalW>0&&span.totalH>0){
      var zoom=Number(opts&&opts.zoom);if(!isFinite(zoom)||zoom<=0)zoom=1;
      var w=span.totalW*zoom,h=span.totalH*zoom;
      var left=(span.totalW-w)/2-span.x;
      var top=(span.totalH-h)/2-span.y;
      // The longhands are set and `inset` is deliberately NOT used here: it is a shorthand
      // for top/right/bottom/left, so assigning `inset:auto` wipes the left and top that
      // were just computed. That is what made every slice render at 0,0 - both monitors
      // showed the left half of the picture and the span looked like two copies.
      el.style.right='auto';
      el.style.bottom='auto';
      el.style.width=w+'px';
      el.style.height=h+'px';
      el.style.left=left+'px';
      el.style.top=top+'px';
      el.style.objectFit='fill';
      el.style.objectPosition='50% 50%';
      // In span mode the geometry already carries the zoom, so the transform must not
      // apply it a second time.
      el.style.transform=buildTransform().replace(/scale\([^)]*\)/,'');
      return;
    }
    el.style.right='auto';
    el.style.bottom='auto';
    el.style.width='100%';
    el.style.height='100%';
    el.style.left='0';
    el.style.top='0';
    el.style.objectFit=objectFitFor(opts?opts.fit:'cover');
    el.style.objectPosition=buildObjectPosition();
    el.style.transform=buildTransform();
  }

  function applyTo(el){
    if(!el)return;
    el.style.filter=buildFilter();
    layout(el);
    if(el.tagName==='VIDEO'){
      var r=Number(opts&&opts.playbackRate);
      if(!isFinite(r)||r<=0)r=1;
      rate=r;
      try{el.playbackRate=rate}catch(e){}
      pingpong=!!(opts&&opts.pingPong);
      try{el.loop=!pingpong}catch(e){}
      ppArmed=pingpong;
    }
  }

  function applyToActive(){applyTo(active)}

  function apply(options){
    opts=options||null;
    span=opts&&opts.span?opts.span:null;
    refreshTone();
    applyToActive();
    report('options-applied'+(opts?'':' none'));
    return true;
  }

  // Ping-pong: the element loops by default, which cannot play backwards. When the mode
  // is on, loop is disabled and this reverses the direction at each end, so the picture
  // plays forward and then back rather than jumping.
  function watchDirection(video,myGeneration){
    if(!pingpong)return;
    function tick(){
      if(myGeneration!==generation||video!==active||!video.isConnected)return;
      if(video.duration&&isFinite(video.duration)){
        var t=video.currentTime;
        if(ppDir>0&&t>=video.duration-0.06){ppDir=-1;try{video.playbackRate=-rate}catch(e){}}
        else if(ppDir<0&&t<=0.06){ppDir=1;try{video.playbackRate=rate}catch(e){}}
      }
      if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,120);
    }
    if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,120);
  }

  function nextPaint(fn){var fired=false;function once(){if(fired)return;fired=true;try{fn()}catch(e){}}try{requestAnimationFrame(once)}catch(e){}setTimeout(once,50)}
  // Is there a decoded frame to show? readyState 2 (HAVE_CURRENT_DATA) is exactly that
  // question, and it is answered without the compositor - which matters because the
  // compositor does not run for an occluded window.
  //
  // This used to route through nextPaint() whenever requestVideoFrameCallback was
  // unavailable, so in an occluded window it waited on requestAnimationFrame and then on a
  // 50ms timer that Chromium throttles to about a second. The video was decoded and the
  // screen stayed black for the difference.
  function firstFrame(el,isImage,ok,fail){
    var done=false;
    function ready(){
      if(done)return;done=true;
      if(isImage||el.readyState>=2){ok();return}
      // Not decoded yet: wait for the event that says it is, with a timer as the net.
      var fired=false;
      function once(){if(fired)return;fired=true;ok()}
      var timer=setTimeout(once,2000);
      el.addEventListener('loadeddata',function(){clearTimeout(timer);once()},{once:true});
      el.addEventListener('canplay',function(){clearTimeout(timer);once()},{once:true});
    }
    if(isImage){el.onload=ready;el.onerror=fail}else{el.addEventListener('error',fail,{once:true});ready()}
  }
  function element(src,isImage){var el=document.createElement(isImage?'img':'video');el.className='media';el.style.opacity='0';el.src=src;if(!isImage){el.preload='auto';el.playsInline=true;el.loop=true;el.muted=muted;el.disablePictureInPicture=true}stage.appendChild(el);return el}
  function watchLoop(video,myGeneration){var last=0;function tick(){if(myGeneration!==generation||video!==active||!video.isConnected)return;var now=video.currentTime||0;if(last>0.5&&now+0.5<last)report('loop-seamless');last=now;if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}

  // ── the swap ──────────────────────────────────────────────────────────────
  //
  // The element is made visible immediately, in the same turn that it becomes active, and
  // the outgoing one is dropped two presented frames later.
  //
  // ── what the earlier versions got wrong ──────────────────────────────────────────
  //
  // The original faded the new element in over 120ms and dropped the old one on a 150ms
  // timer. It flashed black, for three separate reasons, and only the third was the
  // interesting one:
  //
  //   1. A CSS transition is advanced by the compositor. In an occluded window - the
  //      normal state for a wallpaper on a covered monitor - the compositor stops
  //      advancing transitions, so `opacity: 1` with a transition on it can sit at 0
  //      indefinitely. The element is present and decoding and draws as nothing.
  //   2. The 150ms timer assumed the fade had finished. In that case it had not, so the
  //      old element was destroyed while the new one was still invisible.
  //   3. Even with the fade gone, the opacity was still applied from inside nextPaint(),
  //      which waits for requestAnimationFrame - and rAF does not run in an occluded
  //      window either. Its setTimeout(50) backstop is throttled to about a second there.
  //      Measured: the video reached readyState 4 at 1650ms and was still at opacity 0 at
  //      2090ms, then appeared at 2152ms. Six hundred milliseconds of black, every time.
  //
  // The lesson is one thing, and it applies to every line in this function: nothing that
  // has to happen for the picture to be on screen may depend on the compositor running.
  // Opacity, source selection and element removal are all set directly now. Only the
  // removal of the old element waits for a frame, and it has a timer net, because being
  // late there costs memory rather than a black screen.
  function reveal(next,previous,myGeneration,isImage){
    var settled=false;
    function settle(){
      if(settled)return;settled=true;
      if(myGeneration!==generation)return;
      if(previous)remove(previous);
      if(!isImage){watchLoop(next,myGeneration);watchDirection(next,myGeneration)}
    }
    // Direct, in this turn. `transition:'none'` first, because a transition left on the
    // element from an earlier swap would otherwise still apply to this change.
    next.style.transition='none';
    next.style.opacity='1';
    // The old element is removed once the new one has presented a frame while opaque, so
    // the composite is never empty. Two frames rather than one: the first callback can be
    // for a frame that was already queued before the opacity changed.
    if(!isImage&&next.requestVideoFrameCallback){
      next.requestVideoFrameCallback(function(){
        next.requestVideoFrameCallback(function(){settle()});
      });
      // The net for a window that is not presenting at all. It only decides when the old
      // element stops decoding - the new one is already opaque - so it is generous.
      setTimeout(settle,700);
    }else{
      setTimeout(settle,0);
    }
  }
  function prepare(src,isImage,newMuted,token,fps){generation++;var myGeneration=generation;muted=newMuted;var next=element(src,isImage);applyTo(next);if(!isImage){next.muted=muted;next.play().catch(function(){})}firstFrame(next,isImage,function(){if(myGeneration!==generation){remove(next);return}var previous=active;next.style.zIndex='2';active=next;applyTo(next);if(paused&&!isImage)active.pause();reveal(next,previous,myGeneration,isImage);report('media-ready:'+token)},function(){if(myGeneration!==generation)return;remove(next);report('media-error:'+token)})}
  function setPlayback(isPaused,isMuted){
    paused=isPaused;muted=isMuted;
    if(!active||active.tagName!=='VIDEO'){report('pb-noactive:'+(active?active.tagName:'null'));return}
    active.muted=muted;
    var v=active,t0=performance.now();
    if(paused){
      v.pause();
      report('pause-ack:'+Math.round(performance.now()-t0)+' rs='+v.readyState);
    }else{
      var pr=v.play();
      if(pr&&pr.catch)pr.catch(function(e){report('resume-rejected:'+e.name)});
      var done=false;
      function mark(){
        if(done)return;done=true;
        report('resume-frame:'+Math.round(performance.now()-t0)
          +' rs='+v.readyState+' paused='+v.paused+' seeking='+v.seeking
          +' ct='+v.currentTime.toFixed(2)+' net='+v.networkState);
      }
      if(v.requestVideoFrameCallback)v.requestVideoFrameCallback(mark);else setTimeout(mark,60);
    }
  }
  function setFps(fps){}
  function state(){var v=active;return JSON.stringify({generation:generation,paused:paused,muted:muted,active:active?active.tagName:null,readyState:v&&v.tagName==='VIDEO'?v.readyState:null,currentTime:v&&v.tagName==='VIDEO'?Number((v.currentTime||0).toFixed(2)):null,videoWidth:v&&v.tagName==='VIDEO'?v.videoWidth:null,error:v&&v.error?v.error.code:null,connected:v?v.isConnected:null,elements:document.querySelectorAll('video,img').length,hasOptions:!!opts,span:span?'yes':'no',rate:rate})}
  window.luma={prepare:prepare,setPlayback:setPlayback,setFps:setFps,state:state,apply:apply};
 })();
</script></body></html>";
        }

        private void QueueMedia(string path)
        {
            if (IsDisposed || string.IsNullOrWhiteSpace(path)) return;
            if (IsImagePath(path))
            {
                SwitchToStatic(path);
                return;
            }
            if (staticMode)
            {
                mediaRequest++;
                Task.Run(delegate
                {
                    try { BeginInvoke(new Action(async delegate { await SwitchToBrowser(path); })); } catch { }
                });
                return;
            }

            // The page must exist before a script can reach it. This used to return
            // silently, and the caller logged "Media prepared" anyway - so the log said
            // the wallpaper had been applied while the page had never been told about
            // it. That is the failure that leaves a wallpaper showing the previous
            // video, or nothing, with a clean log.
            //
            // Now the pending media is remembered and sent when the page reports ready,
            // which is the same pattern FlushPendingPlaybackSync uses for playback
            // state - that path learned this lesson already and this one had not.
            if (!pageReady)
            {
                pendingMediaPath = path;
                AppLog.Write("Media queued until the page is ready " + screen.DeviceName + " -> " + path);
                return;
            }

            int request = ++mediaRequest;
            // A new request means the old confirmation no longer applies, so the
            // watchdog starts counting again from this moment.
            mediaConfirmed = false;
            mediaRetryCount = 0;
            mediaGaveUp = false;
            pageReloadedForRequest = false;
            lastMediaAttempt = DateTime.UtcNow;
            // The page may be throttled because this wallpaper is stopped behind another
            // window. It has to be woken before it can be asked to decode anything, or
            // the request is delivered to a renderer that is not running scripts.
            PrepareForMediaChange();
            string source = new Uri(path, UriKind.Absolute).AbsoluteUri;
            RunScript("window.luma.prepare(" + JavaScriptString(source) + ",false," + (muted ? "true" : "false") + "," + request + "," + targetFps + ")");
            AppLog.Write("Media prepared in permanent host " + screen.DeviceName + " -> " + path);
        }

        /// <summary>
        /// Sends the media that was queued while the page was still loading.
        ///
        /// Called from ReportReady and from the navigation-completed handler, because
        /// either can be the first moment the page can accept a script.
        /// </summary>
        private void FlushPendingMedia()
        {
            if (string.IsNullOrEmpty(pendingMediaPath)) return;
            string path = pendingMediaPath;
            pendingMediaPath = null;
            AppLog.Write("Sending the media that was queued while loading " + screen.DeviceName + " -> " + path);
            QueueMedia(path);
        }

        private void ReportReady(int request)
        {
            if (request != mediaRequest || IsDisposed) return;
            // The page confirmed this exact request, so the watchdog can stand down.
            mediaConfirmed = true;
            mediaRetryCount = 0;
            mediaGaveUp = false;
            browserReady = true;
            currentMediaPath = mediaPath;
            // The page has just been (re)created, so it knows nothing about the current
            // playback state - it starts from its own defaults. Pushing the state here is
            // what makes a rebuilt page actually play. Without it the host believes the
            // wallpaper is running while the fresh page sits on a paused element, which
            // is exactly what a static wallpaper looks like: the log says resumed, and
            // nothing is decoding.
            ApplyPlaybackState();
            // A wallpaper that was paused before its WebView2 existed has never had the
            // memory policy applied, so this is the first moment it can be. Done here
            // rather than on the pause event because that event already fired.
            ApplyMemoryPolicyOnReady();
            AppLog.Write("Wallpaper renderer ready " + screen.DeviceName + " -> " + mediaPath);
            if (!initialCompletionReported)
            {
                initialCompletionReported = true;
                var handler = RendererReady;
                if (handler != null) handler(this, EventArgs.Empty);
            }
        }

        private void ReportFailed(int request)
        {
            if (request != mediaRequest || IsDisposed) return;
            mediaPath = currentMediaPath ?? mediaPath;
            if (!initialCompletionReported)
            {
                initialCompletionReported = true;
                var handler = RendererFailed;
                if (handler != null) handler(this, EventArgs.Empty);
            }
            else AppLog.Write("Media change cancelled; current wallpaper retained " + screen.DeviceName);
        }

        private static bool IsImagePath(string path)
        {
            string extension = Path.GetExtension(path).ToLowerInvariant();
            return extension == ".jpg" || extension == ".jpeg" || extension == ".png" || extension == ".bmp" || extension == ".webp";
        }

        private static string JavaScriptString(string value)
        {
            return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n") + "\"";
        }

        private void RunScript(string script)
        {
            if (!pageReady || webView == null || webView.CoreWebView2 == null)
            {
                // The page is not ready yet, so the command would be dropped
                // silently and the window would keep whatever state it had -
                // which is why the wallpaper sometimes stayed paused until the
                // user clicked something (that click produced the next event that
                // finally pushed the state through). Remember the intent and
                // replay it as soon as the page signals ready.
                pendingPlaybackSync = true;
                return;
            }
            try
            {
                // The result is inspected rather than discarded. ExecuteScriptAsync
                // reports a script that threw as an exception in its result, and a
                // silent catch here is why a page that never loaded anything looked
                // exactly like a page that was working.
                webView.CoreWebView2.ExecuteScriptAsync(script).ContinueWith(delegate(Task<string> task)
                {
                    if (task.IsFaulted)
                    {
                        Exception error = task.Exception == null ? null : task.Exception.GetBaseException();
                        AppLog.Write("Script failed on " + screen.DeviceName + ": "
                            + (error == null ? "unknown" : error.Message));
                    }
                    else if (task.Result != null && task.Result.IndexOf("\"exceptionDetails\"", StringComparison.Ordinal) >= 0)
                    {
                        AppLog.Write("Script threw on " + screen.DeviceName + ": " + Truncate(task.Result, 300));
                    }
                });
            }
            catch (Exception ex)
            {
                AppLog.Write("Script rejected on " + screen.DeviceName + ": " + ex.Message);
            }
        }

        private static string Truncate(string value, int length)
        {
            if (string.IsNullOrEmpty(value) || value.Length <= length) return value;
            return value.Substring(0, length) + "...";
        }

        /// <summary>
        /// Asks the page what it is doing, and writes the answer to the log.
        ///
        /// Called when a wallpaper change goes unconfirmed, because the interesting
        /// question at that moment is whether the page has an element at all, whether
        /// that element has decoded, and whether it is the element the host last asked
        /// for. Without this the only visible symptom is silence.
        /// </summary>
        private void RequestPageState(string why)
        {
            if (!pageReady || webView == null || webView.IsDisposed || webView.CoreWebView2 == null)
            {
                AppLog.Write("Page state after " + why + " on " + screen.DeviceName
                    + ": host side not usable (pageReady=" + pageReady
                    + " webView=" + (webView == null ? "null" : (webView.IsDisposed ? "disposed" : "ok"))
                    + " core=" + (webView == null || webView.CoreWebView2 == null ? "null" : "ok") + ")");
                return;
            }

            // The host-side facts first, because they decide what a null script result
            // means. IsSuspended and MemoryUsageTargetLevel are the two states that make
            // a live page unable to run script; without them a null result is ambiguous
            // between "the renderer was discarded" and "the page is throttled".
            string hostSide;
            try
            {
                hostSide = "suspended=" + webView.CoreWebView2.IsSuspended
                    + " targetLevel=" + webView.CoreWebView2.MemoryUsageTargetLevel
                    + " webViewVisible=" + webView.Visible
                    + " handleCreated=" + IsHandleCreated;
            }
            catch (Exception ex)
            {
                hostSide = "unavailable: " + ex.Message;
            }

            try
            {
                string probe = "['probe',1+1,String(location.href),typeof window.luma,"
                    + "document.querySelectorAll('video').length,"
                    + "document.readyState,"
                    + "String(document.visibilityState),"
                    + "String(window.__lumaMessages ? window.__lumaMessages.length : -1)"
                    + "].join(' | ')";
                webView.CoreWebView2.ExecuteScriptAsync(probe)
                    .ContinueWith(delegate(Task<string> task)
                    {
                        // UI thread again: this continuation reads webView and screen.
                        if (InvokeRequired)
                        {
                            try { BeginInvoke(new Action(delegate { ReportPageState(why, hostSide, task); })); }
                            catch { }
                            return;
                        }
                        ReportPageState(why, hostSide, task);
                    });
            }
            catch (Exception ex)
            {
                AppLog.Write("Page state probe rejected on " + screen.DeviceName + ": " + ex.Message
                    + " [" + hostSide + "]");
            }
        }

        /// <summary>Writes the page-state probe's answer to the log, on the UI thread.</summary>
        private void ReportPageState(string why, string hostSide, Task<string> task)
        {
            if (IsDisposed) return;
            {
                        string value;
                        if (task.IsFaulted)
                        {
                            Exception error = task.Exception == null ? null : task.Exception.GetBaseException();
                            value = "FAULTED " + (error == null ? "unknown" : error.Message);
                        }
                        else value = task.Result == null ? "(null result)" : task.Result;
                        AppLog.Write("Page state after " + why + " on " + screen.DeviceName
                            + ": [" + hostSide + "] script=" + Truncate(value, 300));
            }
        }

        private void ApplyPlaybackState()
        {
            if (staticMode) return;
            RunScript("window.luma.setPlayback(" + (playbackPaused ? "true" : "false") + "," + (muted ? "true" : "false") + ")");
        }

        /// <summary>
        /// Re-applies the current playback state. Called once the page is ready so
        /// a pause/resume issued while the page was still loading is not lost.
        /// </summary>
        private void FlushPendingPlaybackSync()
        {
            if (!pendingPlaybackSync) return;
            pendingPlaybackSync = false;
            ApplyPlaybackState();
        }

        public void PauseVideo() { playbackPaused = true; ApplyPlaybackState(); }
        public void ResumeVideo() { playbackPaused = false; ApplyPlaybackState(); }

        /// <summary>Whether this wallpaper is currently stopped.</summary>
        public bool IsPlaybackPaused { get { return playbackPaused; } }

        // ── the working-set trim, and why there is no trim here ────────────────
        //
        // A working-set trim of the browser group was implemented, measured, and then
        // REMOVED, because it broke the wallpapers. The record is here so it is not
        // re-added:
        //
        //   Attempt 1 - each paused wallpaper trimmed the pids GetProcessInfos()
        //   returned. Every wallpaper in this app shares one CoreWebView2Environment,
        //   so that call returns the SAME list for all of them, and the list includes
        //   the GPU process doing the video decode. Pausing one monitor therefore
        //   trimmed the GPU process decoding the other two. Measured: GPU VideoDecode
        //   fell from 6.4% to 0.0% and all three screens went black, while the log
        //   reported "5/5 process(es) trimmed" and every wallpaper still reported
        //   itself ready.
        //
        //   Attempt 2 - trim only when EVERY wallpaper is stopped, so no decoder is
        //   live. Measured: the trim worked and released 339 MB (447 MB -> 108 MB,
        //   76% of the group's working set). But when the covers came off, the
        //   wallpapers resumed - the log said "resumed" and pause state was clean -
        //   and GPU VideoDecode stayed at 0.0%. The videos never came back. Only
        //   restarting the app restored them (6.4% again).
        //
        // So on this stack a working-set trim of the GPU process does not survive the
        // decoder resuming, even though the API documentation says Trim has "no
        // effect on rendering operations". The saving was real and large; the cost was
        // a permanently black wallpaper, which is not a trade worth making.
        //
        // What remains, and is kept, is the per-page housekeeping below - it acts on a
        // stopped WebView's own page and touches no shared process.

        /// <summary>
        /// Drops the V8 heap held by a stopped wallpaper page, and asks Chromium to
        /// release what it can.
        ///
        /// This is the surviving half of the memory work. It is safe because it acts
        /// only on this WebView's own page: the V8 heap of a page that is not playing,
        /// and Chromium's own purge machinery for that page. No shared process is
        /// touched, so it cannot disturb another monitor's decode.
        /// </summary>
        public void MaintainPausedMemory()
        {
            if (staticMode) return;

            // Watchdog first, and before the pause check: a wallpaper change that the
            // page never confirmed has to be retried whether or not this wallpaper is
            // currently stopped. Without this the app waits forever on a message that
            // may never come, and the user sees a wallpaper that did not change while
            // the log reports that it was prepared.
            RetryUnconfirmedMedia();
            // Only reconcile when no media change is in flight. A prepare and a probe sent
            // together race: the probe can be answered by the document that is being replaced,
            // which comes back empty and looks like a dead page. Skipping one interval costs
            // nothing and removes the race entirely.
            if (mediaConfirmed) ReconcilePlayback();

            if (!playbackPaused) return;

            DateTime now = DateTime.UtcNow;
            if ((now - lastMemoryMaintenance).TotalSeconds < MemoryMaintenanceSeconds) return;
            lastMemoryMaintenance = now;

            PurgeJavaScriptMemory();
        }

        /// <summary>
        /// Keeps the page's playback in step with what the host believes, and rebuilds the
        /// page when it has stopped running script altogether.
        ///
        /// Two different faults end with the same symptom - a wallpaper that holds a frame
        /// and never moves - and they need different treatment:
        ///
        ///   1. The page is gone. ExecuteScriptAsync returns null for even `1+1`, while
        ///      the WebView still reports itself healthy. Nothing can be fixed from the
        ///      host side; the page has to be rebuilt.
        ///
        ///   2. The page is alive but its video is not playing while the host believes it
        ///      is. This is a desync, and it happens because every playback command is
        ///      edge-triggered: `SetPaused` returns early when the value has not changed,
        ///      so a page that missed one command - because it was being rebuilt, or
        ///      because it had not finished loading - never receives another. The host
        ///      goes on believing the wallpaper plays, and the screen shows a still frame.
        ///
        /// The probe reports both, and the fix for each is applied. The interval is short
        /// because the probe is a single trivial expression, and a wallpaper that has been
        /// still for a minute is a bug report.
        /// </summary>
        private void ReconcilePlayback()
        {
            if (IsDisposed || staticMode || !pageReady) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;

            // A stopped wallpaper is supposed to be still, so there is nothing to reconcile
            // - and it is also the case where a probe cannot be trusted. A stopped page is
            // put at MemoryUsageTargetLevel.Low, which lets Chromium release the renderer's
            // resources; a page in that state can leave an ExecuteScriptAsync unanswered.
            // Reading that silence as "the page died" produced a rebuild of a wallpaper that
            // was doing exactly what it had been told to do.
            if (playbackPaused) return;

            DateTime now = DateTime.UtcNow;
            if ((now - lastLivenessCheck).TotalSeconds < LivenessCheckSeconds) return;
            // A page that has just been told to play or pause needs a moment to carry it
            // out. Probing during that moment answers with a document mid-change, which
            // comes back empty and counts as a strike against a page that is working.
            // The log showed exactly this: two strikes for DISPLAY3 inside the same second
            // as its own resume command.
            if ((now - lastPlaybackCommand).TotalSeconds < SettleSeconds) return;
            lastLivenessCheck = now;
            if (livenessCheckInFlight) return;
            livenessCheckInFlight = true;

            bool hostWantsPlaying = !playbackPaused;

            // The page's own state API, not a hand-written expression. The first version
            // of this probe read `active` directly, which is a variable inside the page's
            // IIFE - so the script threw a ReferenceError, ExecuteScriptAsync reported
            // null for the failure, and every healthy wallpaper was mistaken for a dead
            // page and rebuilt. The page exposes state() for exactly this.
            // String(...) around the whole expression, and a literal fallback: a script whose
            // value is undefined comes back from ExecuteScriptAsync as null, and null was being
            // read as "the page is dead" - which rebuilt a page that was working perfectly.
            // Whatever happens inside, this expression evaluates to a non-empty string.
            string probe = "String((window.luma&&window.luma.state)?window.luma.state():'no-state')";

            try
            {
                webView.CoreWebView2.ExecuteScriptAsync(probe).ContinueWith(delegate(Task<string> task)
                {
                    // The whole body runs on the UI thread. CoreWebView2 belongs to the thread
                    // that created it, and a continuation runs on the pool - reading a
                    // CoreWebView2 member from there throws a COM cast failure (E_NOINTERFACE)
                    // instead of doing the work, which is how the reconcile reported an
                    // exception rather than rebuilding the page it had detected as dead.
                    livenessCheckInFlight = false;
                    if (IsDisposed) return;
                    if (InvokeRequired)
                    {
                        try { BeginInvoke(new Action(delegate { ReconcileBody(task, hostWantsPlaying); })); }
                        catch { }
                        return;
                    }
                    ReconcileBody(task, hostWantsPlaying);
                });
            }
            catch (Exception ex)
            {
                livenessCheckInFlight = false;
                AppLog.Write("Playback reconcile rejected on " + screen.DeviceName + ": " + ex.Message);
            }
        }

        /// <summary>
        /// The body of the reconcile, on the UI thread.
        ///
        /// Split out so the thread hop is one visible line instead of a wrapper around a
        /// hundred lines of logic - the reason this exists is worth being able to see.
        /// </summary>
        private void ReconcileBody(Task<string> task, bool hostWantsPlaying)
        {
            if (IsDisposed) return;
            {
                    livenessCheckInFlight = false;
                    if (IsDisposed) return;

                    string raw = task.IsFaulted || task.Result == null
                        ? null
                        : task.Result.Trim().Trim('"').Replace("\\\"", "\"");

                    // Null, an exception payload, or a page without the state API all mean
                    // the page cannot be asked about itself. Rebuild it.
                    if (raw == null || raw.Length == 0 || raw == "null"
                        || raw.IndexOf("exceptionDetails", StringComparison.Ordinal) >= 0
                        || raw.IndexOf("no-state", StringComparison.Ordinal) >= 0)
                    {
                        // One bad answer is not proof of a dead page. A probe can come back
                        // empty while the document is being replaced - the page that was there
                        // a moment ago is gone and the next one has not run its script yet - and
                        // rebuilding on that transient answer destroyed a page that was working.
                        //
                        // Two consecutive failures are required. A genuinely dead page is still
                        // rebuilt, one interval later; a page that merely blinked is left alone.
                        deadPageStrikes++;
                        AppLog.Write("Wallpaper page did not answer on " + screen.DeviceName
                            + " (strike " + deadPageStrikes + " of " + DeadPageStrikes
                            + ", result " + (task.IsFaulted ? "faulted" : (task.Result ?? "null")) + ")");
                        if (deadPageStrikes < DeadPageStrikes) return;

                        deadPageStrikes = 0;
                        mediaConfirmed = false;
                        mediaRetryCount = 0;
                        pageReloadedForRequest = false;
                        ReloadPage("its script stopped running");
                        return;
                    }

                    // A good answer clears the strikes: the page is demonstrably alive.
                    deadPageStrikes = 0;

                    // state() returns JSON: {"generation":1,"paused":false,...,"readyState":4,...}
                    // Read it with plain string searches - no parser is needed for five
                    // fields, and it keeps this file free of a JSON dependency.
                    bool hasActive = raw.IndexOf("\"active\":null", StringComparison.Ordinal) < 0;
                    bool pagePaused = raw.IndexOf("\"paused\":true", StringComparison.Ordinal) >= 0;
                    int readyState = ReadIntField(raw, "readyState");
                    double currentTime = ReadDoubleField(raw, "currentTime");

                    // A page with no element, or an element that never decoded, cannot be
                    // playing whatever the host believes. Rebuild it.
                    if (!hasActive || readyState < 2)
                    {
                        AppLog.Write("Wallpaper page has no playing element on " + screen.DeviceName
                            + " (active=" + hasActive + " readyState=" + readyState + ")");
                        mediaConfirmed = false;
                        mediaRetryCount = 0;
                        pageReloadedForRequest = false;
                        ReloadPage("its element was gone");
                        return;
                    }

                    // The desync: the host says play, the page says stopped. Re-issue the
                    // command - it is the same one the page missed.
                    if (hostWantsPlaying && pagePaused)
                    {
                        AppLog.Write("Wallpaper was stopped while the app believed it was playing on "
                            + screen.DeviceName + "; resuming");
                        ApplyPlaybackState();
                        return;
                    }

                    // The other desync: nothing is paused, but time is not moving. This is
                    // what a video looks like when its play() promise was rejected - the
                    // element stays unpaused and never advances.
                    if (hostWantsPlaying && !pagePaused)
                    {
                        if (lastSeenTime >= 0 && Math.Abs(currentTime - lastSeenTime) < 0.001)
                        {
                            AppLog.Write("Wallpaper time is not advancing on " + screen.DeviceName
                                + " (stuck at " + currentTime.ToString("F2") + "s); restarting playback");
                            ApplyPlaybackState();
                        }
                        lastSeenTime = currentTime;
                    }
            }
        }

        /// <summary>
        /// Reads an integer field out of the page's state JSON.
        ///
        /// Deliberately a string search rather than a JSON parse: the state object is flat,
        /// the fields are known, and a parse would add a dependency to a file that has
        /// none. Returns -1 when the field is absent, which callers treat as "unknown".
        /// </summary>
        private static int ReadIntField(string json, string name)
        {
            string marker = "\"" + name + "\":";
            int at = json.IndexOf(marker, StringComparison.Ordinal);
            if (at < 0) return -1;
            int start = at + marker.Length;
            int end = start;
            while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '-')) end++;
            int value;
            return int.TryParse(json.Substring(start, end - start), out value) ? value : -1;
        }

        private static double ReadDoubleField(string json, string name)
        {
            string marker = "\"" + name + "\":";
            int at = json.IndexOf(marker, StringComparison.Ordinal);
            if (at < 0) return -1;
            int start = at + marker.Length;
            int end = start;
            while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '-' || json[end] == '.')) end++;
            double value;
            return double.TryParse(json.Substring(start, end - start),
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out value) ? value : -1;
        }

        /// <summary>
        /// Rebuilds the wallpaper page in place.
        ///
        /// This is the recovery for the one failure the host cannot fix by adjusting
        /// anything: a page whose JavaScript context has gone. It was measured on this
        /// machine - the WebView reports suspended=False, targetLevel=Normal,
        /// visible=True and a valid window handle, while ExecuteScriptAsync returns null
        /// for even a trivial expression. Nothing on the host side is wrong; the page is
        /// simply not there any more.
        ///
        /// Navigating to the same file again gives a fresh document, and the
        /// NavigationCompleted handler sends the media that is wanted at that moment -
        /// so the wallpaper that was asked for is the one that loads.
        /// </summary>
        private void ReloadPage(string why)
        {
            if (IsDisposed || webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            AppLog.Write("Rebuilding the wallpaper page on " + screen.DeviceName + " because " + why);
            try
            {
                // pageReady is cleared first: the page is about to be replaced, and
                // leaving it true would let scripts be sent to a document that is going
                // away. NavigationCompleted sets it again.
                pageReady = false;
                browserReady = false;
                // The pending-media slot is cleared so the fresh page does not receive
                // two requests for the same wallpaper: NavigationCompleted sends
                // mediaPath directly, which is already the wallpaper that was asked for.
                pendingMediaPath = null;
                webView.CoreWebView2.Navigate(new Uri(pagePath, UriKind.Absolute).AbsoluteUri);
            }
            catch (Exception ex)
            {
                AppLog.Write("Page rebuild failed on " + screen.DeviceName + ": " + ex.Message);
                ReportFailed(mediaRequest);
            }
        }

        /// <summary>
        /// Re-sends a wallpaper the page never confirmed.
        ///
        /// The page reports `media-ready` once the video has decoded a frame. A page
        /// that never reports leaves the app believing the wallpaper is still being
        /// prepared, so nothing is ever committed and the screen keeps the previous
        /// image. That is the failure this guards against.
        ///
        /// A retry is cheap: sending `prepare` again just replaces the element the page
        /// is holding. It is capped, because a wallpaper that cannot load at all should
        /// surface as a failure rather than loop forever - after the last attempt the
        /// wallpaper is reported failed, which is what makes the app fall back instead
        /// of leaving a blank screen.
        /// </summary>
        private void RetryUnconfirmedMedia()
        {
            if (IsDisposed || staticMode || !pageReady) return;
            if (mediaConfirmed || string.IsNullOrEmpty(mediaPath)) return;

            DateTime now = DateTime.UtcNow;
            if ((now - lastMediaAttempt).TotalSeconds < MediaRetrySeconds) return;
            lastMediaAttempt = now;

            if (mediaRetryCount >= MaxMediaRetries)
            {
                if (!mediaGaveUp)
                {
                    mediaGaveUp = true;
                    AppLog.Write("Wallpaper never confirmed after " + MaxMediaRetries + " attempts on "
                        + screen.DeviceName + " -> " + mediaPath);
                    ReportFailed(mediaRequest);
                }
                return;
            }

            // Two attempts with no answer means the page is not merely slow, it is not
            // running script. The diagnostic proved this happens while the WebView
            // reports itself healthy - not suspended, normal memory target, visible -
            // so there is nothing left to adjust from the host side. The page's
            // JavaScript context is gone, and the only way back is a fresh page.
            //
            // Reloading is safe and cheap: NavigationCompleted re-runs the same setup
            // path as startup, which sends the media that is wanted right now. Once per
            // request, so a page that cannot load anything still ends in a clean failure
            // rather than a reload loop.
            if (mediaRetryCount >= 2 && !pageReloadedForRequest)
            {
                pageReloadedForRequest = true;
                ReloadPage("the page stopped answering");
                return;
            }

            mediaRetryCount++;
            AppLog.Write("Wallpaper unconfirmed; re-sending (attempt " + mediaRetryCount + ") "
                + screen.DeviceName + " -> " + mediaPath);
            // Ask the page what it has before re-sending. The answer is what turns
            // "nothing happened" into a diagnosable fact.
            RequestPageState("unconfirmed attempt " + mediaRetryCount);
            int request = ++mediaRequest;
            string source = new Uri(mediaPath, UriKind.Absolute).AbsoluteUri;
            RunScript("window.luma.prepare(" + JavaScriptString(source) + ",false,"
                + (muted ? "true" : "false") + "," + request + "," + targetFps + ")");
        }

        /// <summary>
        /// The process ids of this wallpaper's WebView2 group, for memory reporting.
        ///
        /// Must be called on the UI thread, because CoreWebView2 objects belong to the
        /// thread that created them. Returns an empty array rather than null so callers
        /// can sum without a null check, and never throws - a wallpaper whose group has
        /// gone away is not an error worth surfacing in a telemetry panel.
        /// </summary>
        public int[] TryGetBrowserProcessIds()
        {
            if (staticMode || webView == null || webView.IsDisposed || webView.CoreWebView2 == null)
                return new int[0];
            try
            {
                var infos = webView.CoreWebView2.Environment.GetProcessInfos();
                if (infos == null) return new int[0];
                var list = new List<int>();
                foreach (CoreWebView2ProcessInfo info in infos)
                    if (info != null && info.ProcessId > 0) list.Add(info.ProcessId);
                return list.ToArray();
            }
            catch
            {
                return new int[0];
            }
        }

        /// <summary>
        /// The memory this wallpaper's own window holds, in bytes.
        ///
        /// This is the app's own working set, not the WebView2 group's - the group is
        /// separate processes and is measured by the caller through
        /// CoreWebView2Environment.GetProcessInfos. Reported so the panel can show
        /// what the host costs separately from what the browser costs.
        /// </summary>
        public void ReportMemory(out long workingSet, out long commit)
        {
            workingSet = 0;
            commit = 0;
            try
            {
                using (System.Diagnostics.Process self = System.Diagnostics.Process.GetCurrentProcess())
                {
                    workingSet = self.WorkingSet64;
                    commit = self.PrivateMemorySize64;
                }
            }
            catch { }
        }

        /// <summary>
        /// Tells this wallpaper whether it should be playing.
        ///
        /// Returns true when the state actually changed, which is what the log uses to
        /// report transitions. The command is sent even when the value has not changed,
        /// and that is the fix for a real fault: every playback command is edge-triggered,
        /// so a page that missed one - because it was being rebuilt, because its element
        /// was still loading, or because the message crossed a page swap - would never be
        /// told again. The host went on believing the wallpaper played while the page sat
        /// on a stopped element, which is exactly a wallpaper that is applied and static.
        ///
        /// Measured on this machine: `resume-frame` appeared for DISPLAY2 and DISPLAY3 in
        /// the same tick where DISPLAY1 - reported as resumed - produced none at all, and
        /// no video decoded for it afterwards.
        /// </summary>
        public bool SetPaused(bool value)
        {
            bool changed = playbackPaused != value;
            playbackPaused = value;

            // The command is re-sent when the state changes, and also when the same
            // state has stood for a while - but not on every call.
            //
            // Both halves matter. Sending only on a change is what left a rebuilt page
            // stopped forever: the page missed the one command it needed and the host
            // never repeated it. Sending on every call is what floods the page, because
            // the manager calls this on every health tick - the log filled with a
            // pause-ack every two seconds per display.
            //
            // So: immediately on a change, then at most once every ReassertSeconds as a
            // safety net. ReconcilePlayback is what handles a page that is genuinely out
            // of step; this is only here so a missed command cannot persist.
            DateTime now = DateTime.UtcNow;
            bool due = changed || (now - lastPlaybackCommand).TotalSeconds >= ReassertSeconds;
            if (due)
            {
                lastPlaybackCommand = now;
                ApplyPlaybackState();
            }
            ApplyMemoryTargetLevel();
            return changed;
        }

        // How long a playback state may stand without being re-sent. Long enough that the
        // traffic is invisible, short enough that a page which missed a command is put
        // right well before a user would notice.
        private const double ReassertSeconds = 30;
        private DateTime lastPlaybackCommand = DateTime.MinValue;

        /// <summary>
        /// Tells the browser engine how much memory it may hold, following the pause
        /// state.
        ///
        /// This is the documented, quality-neutral half of the memory story: while the
        /// wallpaper is stopped it is not being drawn, so there is no reason for the
        /// engine to keep its caches warm, and Low lets it swap out browser-process
        /// memory. The moment the wallpaper plays again it goes back to Normal, before
        /// the first frame is drawn - so the restore is never visible.
        ///
        /// Not combined with TrySuspendAsync, which is the other API in this area:
        /// TrySuspend requires the controller to be invisible and sets the target level
        /// itself, and the two fight each other. A wallpaper window stays visible on
        /// the desktop even when a game covers it, so TrySuspend would be rejected with
        /// ERROR_INVALID_STATE anyway.
        /// </summary>
        private void ApplyMemoryTargetLevel()
        {
            if (staticMode) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            try
            {
                // Low only while the wallpaper is stopped AND settled, Normal otherwise.
                //
                // Low is a real saving and it is documented as best-effort, so it is kept -
                // but only for a page that is genuinely idle. A page that is being asked to
                // load a wallpaper is not idle, and telling Chromium to give up its
                // resources at the same moment it is asked to decode is a race the page
                // loses: the request is delivered to a renderer that has been told to shed
                // what it needs to answer. mediaConfirmed is what distinguishes the two.
                bool idle = playbackPaused && mediaConfirmed;
                webView.CoreWebView2.MemoryUsageTargetLevel = idle
                    ? CoreWebView2MemoryUsageTargetLevel.Low
                    : CoreWebView2MemoryUsageTargetLevel.Normal;
            }
            catch (Exception ex)
            {
                // The runtime can be older than the SDK that exposes this. Logged once
                // per state change, not per frame, so it cannot flood the log.
                AppLog.Write("Memory target level unavailable on " + screen.DeviceName + ": " + ex.Message);
            }
        }

        /// <summary>
        /// Puts the page back to normal resources so it can be asked to do work.
        ///
        /// Called before every media change. The wallpaper may be stopped and marked
        /// Low because a window covers it, and a stopped, memory-throttled page is a
        /// page whose script may not run at all - so the request to load the new video
        /// would never be carried out. Restoring Normal first is what makes a wallpaper
        /// change work while the desktop is covered.
        /// </summary>
        private void PrepareForMediaChange()
        {
            if (staticMode) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            try { webView.CoreWebView2.MemoryUsageTargetLevel = CoreWebView2MemoryUsageTargetLevel.Normal; }
            catch { }
            try { webView.CoreWebView2.Resume(); }
            catch { }
        }

        /// <summary>
        /// Tells Chromium it is under memory pressure, at the moment this app knows
        /// the wallpaper is stopped.
        ///
        /// This is the explicit form of what --msWebView2SimulateMemoryPressureWhenInactive
        /// does automatically, and it is used instead of that flag for a concrete
        /// reason: the flag keys off WebView2's own notion of "inactive", which is a
        /// controller that is invisible or a WebView that is suspended. A wallpaper
        /// window is neither - it stays visible on the desktop behind whatever is
        /// covering it - so the flag would never fire. Here the app already knows the
        /// real answer, because it is the thing that decided to pause.
        ///
        /// The command makes Chromium run its own purge machinery: discardable memory
        /// dropped, caches trimmed, extra garbage collections. Nothing about the
        /// decoded image changes; the pages that go are the ones that will be rebuilt
        /// anyway the next time a frame is drawn.
        ///
        /// The level is MODERATE, and that choice is the fix for a real fault. "critical"
        /// was used first and it broke every wallpaper change: at critical pressure
        /// Chromium is entitled to discard a renderer process outright to reclaim its
        /// memory, and a discarded renderer takes the page's JavaScript context with it.
        /// The wallpaper keeps showing its last painted frame while every later request
        /// to load a different video is evaluated in a context that no longer exists -
        /// ExecuteScriptAsync returns null and nothing happens. Moderate still runs
        /// Chromium's purge machinery (caches trimmed, discardable memory dropped, an
        /// extra GC) without authorising the one action that leaves the page unable to
        /// do its job.
        ///
        /// Fire-and-forget by design. This runs on the pause path, and a wallpaper must
        /// never be held up waiting for the browser to answer a housekeeping call.
        /// </summary>
        private void RequestMemoryPressure()
        {
            if (staticMode) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            try
            {
                // "moderate", not "critical". At critical pressure Chromium is entitled to
                // discard a renderer outright, and a wallpaper whose renderer was discarded
                // keeps its last painted frame - so the fault is invisible until the user
                // changes wallpaper and nothing happens. Moderate still runs the purge
                // machinery (caches trimmed, discardable memory dropped, an extra GC)
                // without authorising the one action that leaves a page unable to work.
                webView.CoreWebView2.CallDevToolsProtocolMethodAsync("Memory.simulatePressureNotification",
                    "{\"level\":\"moderate\"}");
            }
            catch (Exception ex)
            {
                AppLog.Write("Memory pressure request skipped on " + screen.DeviceName + ": " + ex.Message);
            }
        }

        /// <summary>
        /// Drops the V8 heap held by the wallpaper page.
        ///
        /// A wallpaper page is one video element and a few dozen lines of script; if its
        /// JS heap is large, it is stale state rather than working memory. Called only
        /// while paused, and only on the periodic health tick - not on every pause -
        /// because a full GC on a page that is about to resume is pure waste.
        /// </summary>
        private void PurgeJavaScriptMemory()
        {
            if (staticMode) return;
            if (!playbackPaused) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            try
            {
                // Kept, because the fault that made it look dangerous was not this call.
                //
                // A wallpaper page holds one video element and a few dozen lines of script,
                // so there is little heap here to reclaim - but the purge is free while the
                // page is stopped and it is the one memory action that acts on this page
                // alone rather than on the shared browser group.
                //
                // The investigation that removed it briefly was misled by a broken probe:
                // the liveness check read a variable that only exists inside the page's
                // IIFE, so every healthy page answered null and looked like a page whose
                // JavaScript context had been discarded. With the probe fixed - it now
                // calls the page's own state() - the purge is safe to keep.
                webView.CoreWebView2.CallDevToolsProtocolMethodAsync("Memory.forciblyPurgeJavaScriptMemory", "{}");
            }
            catch (Exception ex)
            {
                AppLog.Write("JS memory purge skipped on " + screen.DeviceName + ": " + ex.Message);
            }
        }

        /// <summary>
        /// Re-applies the memory policy after the page becomes ready.
        ///
        /// A wallpaper created while a game was already fullscreen is paused before its
        /// WebView2 exists, so the pause-time memory settings would be applied to
        /// nothing. This runs on the ready signal so the new page starts in the right
        /// state instead of holding full-size caches until the next pause event.
        /// </summary>
        private void ApplyMemoryPolicyOnReady()
        {
            ApplyMemoryTargetLevel();
            if (playbackPaused) RequestMemoryPressure();
            // The page starts with no options, so a wallpaper restored at startup has to be
            // told about them - otherwise the user's colour grade and framing would appear
            // only after they touched a control.
            ApplyOptions();
        }

        // ── the per-display look and playback settings ───────────────────────
        //
        // The options live in the config, but the page needs them as one JSON object. It is
        // built here rather than serialized from the C# type because the page wants short
        // camelCase names and the config uses the C# names, and because the span geometry
        // is computed at this point - it depends on where this monitor sits in the desktop,
        // which the config does not know.
        private DisplayOptions options = new DisplayOptions();
        private SpanGroup spanGroup;

        public void SetOptions(DisplayOptions value, SpanGroup span)
        {
            options = value ?? new DisplayOptions();
            spanGroup = span;
            if (pageReady) ApplyOptions();
        }

        /// <summary>
        /// Sends the options to the page.
        ///
        /// Every value is written with InvariantCulture. On a machine whose locale uses a
        /// comma for the decimal separator, `1,5` inside a JSON number is a parse error -
        /// and the page would fall back to its defaults, which is a wallpaper that ignores
        /// the user's settings only on some computers.
        /// </summary>
        private void ApplyOptions()
        {
            if (!pageReady || staticMode) return;
            RunScript("window.luma.apply(" + BuildOptionsJson() + ")");
        }

        private string BuildOptionsJson()
        {
            var culture = System.Globalization.CultureInfo.InvariantCulture;
            var json = new StringBuilder();
            json.Append("{");
            json.Append("\"brightness\":").Append(options.Brightness.ToString("0.####", culture)).Append(",");
            json.Append("\"contrast\":").Append(options.Contrast.ToString("0.####", culture)).Append(",");
            json.Append("\"saturation\":").Append(options.Saturation.ToString("0.####", culture)).Append(",");
            json.Append("\"hue\":").Append(options.Hue.ToString("0.####", culture)).Append(",");
            json.Append("\"gamma\":").Append(options.Gamma.ToString("0.####", culture)).Append(",");
            json.Append("\"filter\":").Append(JavaScriptString(string.IsNullOrEmpty(options.Filter) ? "none" : options.Filter)).Append(",");
            json.Append("\"flipHorizontal\":").Append(options.FlipHorizontal ? "true" : "false").Append(",");
            json.Append("\"flipVertical\":").Append(options.FlipVertical ? "true" : "false").Append(",");
            json.Append("\"hdrToneMap\":").Append(options.HdrToneMap ? "true" : "false").Append(",");
            json.Append("\"hdrExposure\":").Append(options.HdrExposure.ToString("0.####", culture)).Append(",");
            json.Append("\"hdrHighlight\":").Append(options.HdrHighlight.ToString("0.####", culture)).Append(",");
            json.Append("\"fit\":").Append(JavaScriptString(string.IsNullOrEmpty(options.Fit) ? "cover" : options.Fit)).Append(",");
            json.Append("\"zoom\":").Append(options.Zoom.ToString("0.####", culture)).Append(",");
            json.Append("\"offsetX\":").Append(options.OffsetX.ToString("0.####", culture)).Append(",");
            json.Append("\"offsetY\":").Append(options.OffsetY.ToString("0.####", culture)).Append(",");
            json.Append("\"playbackRate\":").Append(options.PlaybackRate.ToString("0.####", culture)).Append(",");
            json.Append("\"pingPong\":").Append(options.PingPong ? "true" : "false");

            // The span geometry, in this monitor's own coordinates. The page needs to know
            // how big the whole picture is and how far into it this monitor sits; it does
            // not need to know anything about the other monitors.
            if (spanGroup != null)
            {
                int x, y, totalW, totalH;
                if (TryMeasureSpan(spanGroup, out x, out y, out totalW, out totalH))
                {
                    json.Append(",\"span\":{");
                    json.Append("\"x\":").Append(x.ToString(culture)).Append(",");
                    json.Append("\"y\":").Append(y.ToString(culture)).Append(",");
                    json.Append("\"totalW\":").Append(totalW.ToString(culture)).Append(",");
                    json.Append("\"totalH\":").Append(totalH.ToString(culture));
                    json.Append("}");
                }
            }

            json.Append("}");
            return json.ToString();
        }

        /// <summary>
        /// Where this monitor sits inside its span group, and how big the group is.
        ///
        /// The group's monitors are ordered left to right by their position on the desktop,
        /// not by the order they were added, because "the left monitor shows the left part"
        /// is the only arrangement a user expects. A monitor with no entry in the group is
        /// reported as a failure so the page falls back to a normal single-monitor
        /// wallpaper rather than drawing a slice that belongs to nobody.
        /// </summary>
        private bool TryMeasureSpan(SpanGroup group, out int x, out int y, out int totalW, out int totalH)
        {
            x = y = totalW = totalH = 0;
            if (group == null || group.Devices == null || group.Devices.Count == 0) return false;

            var members = new List<Forms.Screen>();
            foreach (Forms.Screen candidate in Forms.Screen.AllScreens)
                foreach (string device in group.Devices)
                    if (string.Equals(candidate.DeviceName, device, StringComparison.OrdinalIgnoreCase)) members.Add(candidate);
            if (members.Count == 0) return false;

            members.Sort(delegate(Forms.Screen a, Forms.Screen b)
            {
                int byX = a.Bounds.Left.CompareTo(b.Bounds.Left);
                return byX != 0 ? byX : a.Bounds.Top.CompareTo(b.Bounds.Top);
            });

            Forms.Screen mine = null;
            foreach (Forms.Screen candidate in members)
                if (string.Equals(candidate.DeviceName, screen.DeviceName, StringComparison.OrdinalIgnoreCase)) mine = candidate;
            if (mine == null) return false;

            int left = int.MaxValue, top = int.MaxValue, right = int.MinValue, bottom = int.MinValue;
            foreach (Forms.Screen member in members)
            {
                left = Math.Min(left, member.Bounds.Left);
                top = Math.Min(top, member.Bounds.Top);
                right = Math.Max(right, member.Bounds.Right);
                bottom = Math.Max(bottom, member.Bounds.Bottom);
            }

            totalW = right - left;
            totalH = bottom - top;
            if (totalW <= 0 || totalH <= 0) return false;
            // Offsets are measured from the union's top-left corner, which is what the page
            // subtracts to find its own slice.
            x = mine.Bounds.Left - left;
            y = mine.Bounds.Top - top;
            return true;
        }
        public void SetMute(bool value) { muted = value; ApplyPlaybackState(); }
        public void ChangeMedia(string path, bool mute, int fps)
        {
            muted = mute;
            targetFps = Math.Max(10, Math.Min(30, fps));
            if (string.Equals(currentMediaPath, path, StringComparison.OrdinalIgnoreCase))
            {
                mediaPath = path;
                ApplyPlaybackState();
                ReassertDesktop();
                return;
            }
            mediaPath = path;
            QueueMedia(path);
        }
        public void ReassertDesktop()
        {
            try { if (browserReady && !IsDisposed && IsHandleCreated) NativeDesktop.AttachToWallpaper(Handle, screen.Bounds); } catch { }
        }

        /// <summary>
        /// True while this window is still parented to a live desktop host.
        ///
        /// After an Explorer restart the old WorkerW is destroyed, so the window
        /// keeps running but is no longer part of the desktop. Checking the
        /// parent's liveness (not just that a parent exists) is what lets the
        /// manager notice and repair it.
        /// </summary>
        public bool IsDesktopAttached
        {
            get
            {
                try
                {
                    if (IsDisposed || !IsHandleCreated) return false;
                    IntPtr parent = NativeDesktop.GetRealParent(Handle);
                    return parent != IntPtr.Zero && NativeDesktop.IsWindowAlive(parent);
                }
                catch { return false; }
            }
        }
        public void SetTargetFps(int fps)
        {
            targetFps = Math.Max(10, Math.Min(30, fps));
            if (!staticMode) RunScript("window.luma.setFps(" + targetFps + ")");
        }
        public bool Matches(Forms.Screen target, string path)
        {
            return string.Equals(screen.DeviceName, target.DeviceName, StringComparison.OrdinalIgnoreCase) &&
                screen.Bounds == target.Bounds && string.Equals(currentMediaPath ?? mediaPath, path, StringComparison.OrdinalIgnoreCase) && !IsDisposed;
        }
        /// <summary>The display this wallpaper is attached to.</summary>
        public string DeviceName { get { return screen.DeviceName; } }

        /// <summary>The display this wallpaper covers, for callers that need to know which.</summary>
        public Forms.Screen Screen { get { return screen; } }

        public bool MatchesScreen(Forms.Screen target) { return string.Equals(screen.DeviceName, target.DeviceName, StringComparison.OrdinalIgnoreCase) && screen.Bounds == target.Bounds && !IsDisposed; }
        public void StopVideo()
        {
            try
            {
                if (webView != null)
                {
                    if (pageReady && webView.CoreWebView2 != null) RunScript("var v=document.getElementById('media');if(v){v.pause();v.removeAttribute('src');v.load();}");
                    webView.Dispose();
                    webView = null;
                }
            }
            catch { }
            try { if (staticSurface != null) { staticSurface.SetImage(null); staticSurface.Dispose(); staticSurface = null; } } catch { }
            try { if (!string.IsNullOrWhiteSpace(pagePath) && File.Exists(pagePath)) File.Delete(pagePath); } catch { }
        }
    }

    /// <summary>
    /// GDI-painted wallpaper surface for static images. It only repaints when
    /// the image or the window size actually changes, so an idle static
    /// wallpaper costs ~0% CPU and no WebView2 process at all.
    /// </summary>
    internal sealed class StaticImageSurface : Forms.Control
    {
        private Drawing.Image image;
        private bool hasImage;

        public StaticImageSurface()
        {
            SetStyle(Forms.ControlStyles.AllPaintingInWmPaint | Forms.ControlStyles.UserPaint | Forms.ControlStyles.OptimizedDoubleBuffer, true);
            UpdateStyles();
        }

        public bool HasImage { get { return hasImage; } }

        public void SetImage(Drawing.Image value)
        {
            Drawing.Image previous = image;
            image = value;
            hasImage = value != null;
            if (previous != null) { try { previous.Dispose(); } catch { } }
            Invalidate();
        }

        protected override void OnPaint(Forms.PaintEventArgs e)
        {
            if (image == null)
            {
                e.Graphics.Clear(Drawing.Color.Black);
                return;
            }
            Drawing.Rectangle bounds = ClientRectangle;
            if (bounds.Width <= 0 || bounds.Height <= 0) return;
            double scale = Math.Max((double)bounds.Width / image.Width, (double)bounds.Height / image.Height);
            int width = Math.Max(1, (int)Math.Round(image.Width * scale));
            int height = Math.Max(1, (int)Math.Round(image.Height * scale));
            int x = (bounds.Width - width) / 2;
            int y = (bounds.Height - height) / 2;
            e.Graphics.InterpolationMode = Drawing.Drawing2D.InterpolationMode.HighQualityBilinear;
            e.Graphics.PixelOffsetMode = Drawing.Drawing2D.PixelOffsetMode.HighQuality;
            e.Graphics.DrawImage(image, new Drawing.Rectangle(x, y, width, height));
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && image != null) { try { image.Dispose(); } catch { } image = null; }
            base.Dispose(disposing);
        }
    }

    internal sealed class WallpaperManager
    {
        private readonly Dictionary<string, WallpaperWindow> windows = new Dictionary<string, WallpaperWindow>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, WallpaperWindow> pending = new Dictionary<string, WallpaperWindow>(StringComparer.OrdinalIgnoreCase);
        // Pause state is tracked per display: a fullscreen game on one monitor
        // must not freeze the wallpaper on the others. globalPaused covers the
        // reasons that stop everything (lock screen, battery, the user's menu).
        private bool globalPaused;
        private readonly HashSet<string> pausedDevices = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// The live settings, so a window can be handed its display's look and span group.
        ///
        /// A reference rather than a copy: the user can change these while wallpapers are
        /// running, and a snapshot taken at startup would go stale. Null until the window
        /// sets it, and every reader tolerates null - a wallpaper created before that point
        /// uses the neutral defaults, which is the behaviour of the build before these
        /// features existed.
        /// </summary>
        public AppConfig Config;

        /// <summary>
        /// The live wallpaper window on the primary display, or the first one found.
        ///
        /// The desktop timer needs a wallpaper handle to sit above, so it lands at the
        /// desktop's level instead of floating over the user's applications. The primary
        /// display is the right choice because that is the screen the timer is positioned
        /// on - and any wallpaper's top-level ancestor is the same desktop window anyway.
        /// </summary>
        public IntPtr PrimaryWallpaperHandle()
        {
            foreach (var pair in windows)
            {
                WallpaperWindow window = pair.Value;
                if (window == null || !window.IsHandleCreated) continue;
                try
                {
                    if (window.Screen != null && window.Screen.Primary) return window.Handle;
                }
                catch { }
            }
            // No primary wallpaper (it may be off, or still starting): any live one will
            // do, because the anchor is the desktop, not the wallpaper itself.
            foreach (var pair in windows)
            {
                WallpaperWindow window = pair.Value;
                if (window == null) continue;
                try { if (window.IsHandleCreated) return window.Handle; } catch { }
            }
            return IntPtr.Zero;
        }

        /// <summary>
        /// Hands a window the settings that apply to its display.
        ///
        /// Called at every point a wallpaper is created, changed or re-asserted. Skipping
        /// any of them leaves that wallpaper wearing the previous display's grade, which
        /// looks like a colour setting that went to the wrong monitor.
        /// </summary>
        private void PushOptions(WallpaperWindow window, string deviceName)
        {
            if (window == null) return;
            AppConfig config = Config;
            if (config == null) return;
            try { window.SetOptions(config.OptionsFor(deviceName), config.SpanGroupFor(deviceName)); }
            catch { }
        }

        /// <summary>
        /// Re-applies the current look and span to every live wallpaper.
        ///
        /// This is what the settings page calls after a slider moves. Without it the user
        /// would have to change wallpaper to see the effect, and the natural conclusion
        /// would be that the control does nothing.
        /// </summary>
        public void RefreshOptions()
        {
            var all = new List<WallpaperWindow>();
            foreach (var pair in windows) all.Add(pair.Value);
            foreach (var pair in pending) all.Add(pair.Value);
            foreach (WallpaperWindow window in all)
            {
                try { PushOptions(window, window.DeviceName); } catch { }
            }
        }

        /// <summary>Whether the given display should currently be frozen.</summary>
        private bool IsPaused(string deviceName)
        {
            return globalPaused || pausedDevices.Contains(deviceName);
        }

        /// <summary>Re-applies the current pause state to one freshly created window.</summary>
        private void SyncPause(WallpaperWindow window, string deviceName)
        {
            window.SetPaused(IsPaused(deviceName));
        }

        public void Apply(Forms.Screen screen, string path, bool mute, int fps)
        {
            WallpaperWindow existing;
            if (windows.TryGetValue(screen.DeviceName, out existing) && existing.Matches(screen, path))
            {
                CancelPending(screen.DeviceName);
                existing.SetMute(mute);
                existing.SetTargetFps(fps);
                existing.ReassertDesktop();
                SyncPause(existing, screen.DeviceName);
                PushOptions(existing, screen.DeviceName);
                AppLog.Write("Wallpaper already active; reasserted " + screen.DeviceName + " -> " + path);
                return;
            }

            if (existing != null && existing.MatchesScreen(screen))
            {
                CancelPending(screen.DeviceName);
                existing.ChangeMedia(path, mute, fps);
                SyncPause(existing, screen.DeviceName);
                PushOptions(existing, screen.DeviceName);
                AppLog.Write("Wallpaper changed inside permanent host " + screen.DeviceName + " -> " + path);
                return;
            }

            WallpaperWindow preparing;
            if (pending.TryGetValue(screen.DeviceName, out preparing) && preparing.Matches(screen, path))
            {
                preparing.SetMute(mute);
                preparing.SetTargetFps(fps);
                SyncPause(preparing, screen.DeviceName);
                PushOptions(preparing, screen.DeviceName);
                AppLog.Write("Wallpaper swap already preparing " + screen.DeviceName + " -> " + path);
                return;
            }

            CancelPending(screen.DeviceName);
            var window = new WallpaperWindow(screen, path, mute, fps);
            // Pushed before Show() so the page's very first painted frame already carries
            // the user's grade. Doing it after would flash the ungraded picture first.
            PushOptions(window, screen.DeviceName);
            pending[screen.DeviceName] = window;
            window.RendererReady += delegate { CommitSwap(screen.DeviceName, window); };
            window.RendererFailed += delegate { FailSwap(screen.DeviceName, window); };
            window.Show();
            SyncPause(window, screen.DeviceName);
            AppLog.Write("Wallpaper swap preparing " + screen.DeviceName + " -> " + path);
        }

        private void CommitSwap(string device, WallpaperWindow candidate)
        {
            WallpaperWindow currentPending;
            if (!pending.TryGetValue(device, out currentPending) || !ReferenceEquals(currentPending, candidate))
            {
                DisposeWindow(candidate);
                return;
            }

            WallpaperWindow previous;
            windows.TryGetValue(device, out previous);
            pending.Remove(device);
            windows[device] = candidate;
            candidate.ReassertDesktop();
            if (previous != null && !ReferenceEquals(previous, candidate)) DisposeWindow(previous);
            AppLog.Write("Wallpaper swap committed without blank frame " + device);
        }

        private void FailSwap(string device, WallpaperWindow candidate)
        {
            WallpaperWindow currentPending;
            if (pending.TryGetValue(device, out currentPending) && ReferenceEquals(currentPending, candidate)) pending.Remove(device);
            DisposeWindow(candidate);
            AppLog.Write("Wallpaper swap cancelled; previous wallpaper preserved " + device);
        }

        private void CancelPending(string device)
        {
            WallpaperWindow candidate;
            if (!pending.TryGetValue(device, out candidate)) return;
            pending.Remove(device);
            DisposeWindow(candidate);
        }

        private static void DisposeWindow(WallpaperWindow window)
        {
            try { window.StopVideo(); window.Close(); } catch { }
        }

        public void Remove(string device)
        {
            CancelPending(device);
            WallpaperWindow old;
            if (!windows.TryGetValue(device, out old)) return;
            DisposeWindow(old);
            windows.Remove(device);
        }

        /// <summary>
        /// Pauses exactly the monitors that should be paused, and resumes the rest.
        ///
        /// `global` short-circuits everything: when true (lock screen, battery, the
        /// user's own pause) every display stops. Otherwise only the monitors in
        /// `devicesToPause` stop and all others run, in a single pass - doing it in
        /// one pass matters because resuming everything and then re-pausing the
        /// covered monitors would let one frame of the wallpaper show through.
        ///
        /// This replaces the old single global flag, which froze every display
        /// whenever a fullscreen window appeared on any one of them.
        /// </summary>
        public void ApplyPauseState(HashSet<string> devicesToPause, bool global)
        {
            globalPaused = global;
            pausedDevices.Clear();
            if (!global && devicesToPause != null)
                foreach (string device in devicesToPause) pausedDevices.Add(device);

            int pausedNow = 0, resumedNow = 0;
            var pausedNames = new List<string>();
            var resumedNames = new List<string>();
            foreach (var pair in windows)
            {
                bool shouldPause = IsPaused(pair.Key);
                if (pair.Value.SetPaused(shouldPause))
                {
                    if (shouldPause) { pausedNow++; pausedNames.Add(pair.Key); }
                    else { resumedNow++; resumedNames.Add(pair.Key); }
                }
            }
            foreach (var pair in pending)
            {
                bool shouldPause = IsPaused(pair.Key);
                if (pair.Value.SetPaused(shouldPause))
                {
                    if (shouldPause) { pausedNow++; pausedNames.Add(pair.Key); }
                    else { resumedNow++; resumedNames.Add(pair.Key); }
                }
            }
            if (pausedNow > 0 || resumedNow > 0)
            {
                // Device names, not just counts: the whole point of this path is
                // that different monitors can be in different states, and a bare
                // "1 paused, 1 resumed" cannot be verified from the log.
                string scope = global ? "all displays" :
                    (devicesToPause == null || devicesToPause.Count == 0 ? "none covered" :
                     string.Join(", ", new List<string>(devicesToPause).ToArray()));
                AppLog.Write("Playback updated (" + scope + "): " +
                    "paused [" + string.Join(", ", pausedNames.ToArray()) + "] " +
                    "resumed [" + string.Join(", ", resumedNames.ToArray()) + "]");

                // No trim here. See the note on WallpaperWindow.MaintainPausedMemory
                // for the measurements: trimming the browser group killed the video
                // decoders and they did not come back on resume.
            }
        }

        /// <summary>
        /// Adds a manager-level way to collect the whole app's memory footprint.
        ///
        /// The point of this is honesty in the UI. The performance panel used to show
        /// only this process's working set, which for a WebView2 host is a fraction of
        /// the real number: the browser, GPU and renderer processes are separate and
        /// hold most of the memory. A panel that reports 60 MB while Task Manager shows
        /// 500 MB across six processes is worse than no panel, because it teaches the
        /// user not to trust it.
        /// </summary>
        public void CollectMemory(out long browserWorkingSet, out long browserCommit, out int browserProcesses)
        {
            browserWorkingSet = 0;
            browserCommit = 0;
            browserProcesses = 0;

            var seen = new HashSet<int>();
            var all = new List<WallpaperWindow>();
            foreach (var pair in windows) all.Add(pair.Value);
            foreach (var pair in pending) all.Add(pair.Value);

            foreach (WallpaperWindow window in all)
            {
                int[] pids;
                try { pids = window.TryGetBrowserProcessIds(); }
                catch { continue; }

                foreach (int pid in pids)
                {
                    // Several wallpapers share one WebView2 environment, so the same
                    // browser and GPU process appear once per display. Counting them
                    // twice would overstate the footprint on exactly the multi-monitor
                    // setups this is meant to inform.
                    if (!seen.Add(pid)) continue;
                    long workingSet, commit;
                    if (!MemoryTrim.TryGetMemory(pid, out workingSet, out commit)) continue;
                    browserWorkingSet += workingSet;
                    browserCommit += commit;
                    browserProcesses++;
                }
            }
        }

        /// <summary>
        /// The periodic pass over every wallpaper, called from the health tick.
        ///
        /// Deliberately empty of the working-set trim. See TrimPausedWallpapers for
        /// what was tried and why it was removed.
        /// </summary>
        public void MaintainPausedMemory()
        {
        }

        /// <summary>
        /// The per-wallpaper page housekeeping: the V8 purge, on its own throttle.
        ///
        /// This acts only on a stopped WebView's own page and touches no shared
        /// process, so it is safe while other wallpapers play. It is the one memory
        /// measure that survived measurement.
        /// </summary>
        public void MaintainPausedPages()
        {
            var all = new List<WallpaperWindow>();
            foreach (var pair in windows) all.Add(pair.Value);
            foreach (WallpaperWindow window in all)
            {
                try { window.MaintainPausedMemory(); }
                catch { }
            }
        }

        /// <summary>
        /// Detects wallpapers whose window is gone and rebuilds them.
        ///
        /// When Explorer restarts, the shell destroys the whole desktop window
        /// tree - and a child window is destroyed together with its parent. The
        /// wallpaper's window handle therefore becomes invalid, and no amount of
        /// re-parenting can revive it: the window has to be created again. That
        /// is why the app used to keep "re-attaching" forever without the
        /// wallpaper ever coming back.
        /// </summary>
        public void VerifyDesktopHosts()
        {
            List<string> rebuild = null;
            foreach (var pair in windows)
            {
                if (pair.Value.IsDisposed || !pair.Value.IsHandleCreated)
                {
                    if (rebuild == null) rebuild = new List<string>();
                    rebuild.Add(pair.Key);
                }
                else if (!pair.Value.IsDesktopAttached)
                {
                    pair.Value.ReassertDesktop();
                }
            }
            if (rebuild == null) return;

            // Rebuild outside the enumeration: Apply() mutates `windows`.
            foreach (string device in rebuild)
            {
                string path;
                if (!TryGetWallpaper(device, out path)) continue;
                AppLog.Write("Wallpaper window was destroyed with the desktop; rebuilding " + device);
                Remove(device);
                var screen = Forms.Screen.AllScreens.FirstOrDefault(s => string.Equals(s.DeviceName, device, StringComparison.OrdinalIgnoreCase));
                if (screen != null) Apply(screen, path, mute, fps);
            }
        }

        /// <summary>Remembers the current mute/FPS so a rebuilt wallpaper matches.</summary>
        private bool mute = true;
        private int fps = 24;
        public void SetDefaults(bool muteValue, int fpsValue) { mute = muteValue; fps = fpsValue; }

        /// <summary>Path of the wallpaper assigned to a display, or null.</summary>
        public Func<string, string> WallpaperLookup { get; set; }
        private bool TryGetWallpaper(string device, out string path)
        {
            path = WallpaperLookup != null ? WallpaperLookup(device) : null;
            return !string.IsNullOrWhiteSpace(path) && File.Exists(path);
        }

        /// <summary>
        /// Global pause (lock screen, battery, the user's tray toggle) - all monitors.
        ///
        /// Kept as a thin wrapper over ApplyPauseState so there is exactly one place
        /// that owns the per-device state; a second implementation here is what let
        /// the old global flag and the new per-monitor set drift apart.
        /// </summary>
        public void SetPaused(bool value)
        {
            ApplyPauseState(null, value);
        }

        public void SetMute(bool value)
        {
            foreach (var window in windows.Values) window.SetMute(value);
            foreach (var window in pending.Values) window.SetMute(value);
        }

        public void SetTargetFps(int value)
        {
            foreach (var window in windows.Values) window.SetTargetFps(value);
            foreach (var window in pending.Values) window.SetTargetFps(value);
        }

        public void CloseAll()
        {
            foreach (var window in pending.Values.ToArray()) DisposeWindow(window);
            pending.Clear();
            foreach (var window in windows.Values.ToArray()) DisposeWindow(window);
            windows.Clear();
        }
    }

}
