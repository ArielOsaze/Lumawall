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

        [STAThread]
        private static void Main()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
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
                    if (value.MonitorVideos == null) value.MonitorVideos = new Dictionary<string, string>();
                    if (value.Library == null) value.Library = new List<string>();
                    if (value.DisplayProfiles == null) value.DisplayProfiles = new Dictionary<string, Dictionary<string, string>>();
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
        /// Walks every visible top-level window and collects the monitors each
        /// one completely covers.
        /// </summary>
        private static List<string> ScanCoveringWindows(bool requireZoomed)
        {
            var covered = new List<string>();
            uint ownPid = (uint)Process.GetCurrentProcess().Id;

            EnumWindows(delegate(IntPtr hwnd, IntPtr param)
            {
                if (!IsWindowVisible(hwnd)) return true;
                if (IsIconic(hwnd)) return true;
                if (requireZoomed && !IsZoomed(hwnd)) return true;

                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid == ownPid) return true;
                if (IsShellDesktopWindow(hwnd) || IsOverlayWindow(hwnd)) return true;
                if (IsNonAppWindow(hwnd)) return true;

                RECT rect;
                if (!GetWindowRect(hwnd, out rect)) return true;
                if (rect.Right <= rect.Left || rect.Bottom <= rect.Top) return true;

                foreach (var screen in Forms.Screen.AllScreens)
                {
                    if (covered.Contains(screen.DeviceName)) continue;
                    var b = screen.Bounds;
                    int overlapW = Math.Min(rect.Right, b.Right) - Math.Max(rect.Left, b.Left);
                    int overlapH = Math.Min(rect.Bottom, b.Bottom) - Math.Max(rect.Top, b.Top);
                    // 2% tolerance: maximized windows are inset by the invisible
                    // resize border, and DPI rounding can shave a pixel or two.
                    if (overlapW >= b.Width * 0.98 && overlapH >= b.Height * 0.98)
                        covered.Add(screen.DeviceName);
                }
                return true;
            }, IntPtr.Zero);

            return covered;
        }

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
 html,body,#stage{width:100%;height:100%;margin:0;overflow:hidden;background:transparent}
 .media{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;opacity:1;z-index:1}
 </style></head><body><div id='stage'></div><script>
 (function(){
  var stage=document.getElementById('stage'),active=null,generation=0,paused=false,muted=true;
  function report(v){try{window.chrome.webview.postMessage(v)}catch(e){}}
  function remove(el){if(!el)return;try{el.pause()}catch(e){};try{el.removeAttribute('src');el.load()}catch(e){};try{el.remove()}catch(e){}}
  function firstFrame(el,isImage,ok,fail){var done=false;function ready(){if(done)return;done=true;if(!isImage&&el.requestVideoFrameCallback)el.requestVideoFrameCallback(ok);else requestAnimationFrame(ok)}if(isImage){el.onload=ready;el.onerror=fail}else{el.addEventListener('loadeddata',ready,{once:true});el.addEventListener('canplay',ready,{once:true});el.addEventListener('error',fail,{once:true});if(el.readyState>=2)ready()}}
  function element(src,isImage){var el=document.createElement(isImage?'img':'video');el.className='media';el.style.opacity='0';el.src=src;if(!isImage){el.preload='auto';el.playsInline=true;el.loop=true;el.muted=muted;el.disablePictureInPicture=true}stage.appendChild(el);return el}
  function watchLoop(video,myGeneration){var last=0;function tick(){if(myGeneration!==generation||video!==active||!video.isConnected)return;var now=video.currentTime||0;if(last>0.5&&now+0.5<last)report('loop-seamless');last=now;if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}
  function prepare(src,isImage,newMuted,token,fps){generation++;var myGeneration=generation;muted=newMuted;var next=element(src,isImage);if(!isImage){next.muted=muted;next.play().catch(function(){})}firstFrame(next,isImage,function(){if(myGeneration!==generation){remove(next);return}var previous=active;next.style.zIndex='2';next.style.transition='opacity 120ms linear';active=next;if(paused&&!isImage)active.pause();requestAnimationFrame(function(){next.style.opacity='1';setTimeout(function(){next.style.transition='';if(previous)remove(previous);if(!isImage)watchLoop(next,myGeneration)},150)});report('media-ready:'+token)},function(){if(myGeneration!==generation)return;remove(next);report('media-error:'+token)})}
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
  window.luma={prepare:prepare,setPlayback:setPlayback,setFps:setFps};
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
            if (!pageReady) return;
            int request = ++mediaRequest;
            string source = new Uri(path, UriKind.Absolute).AbsoluteUri;
            RunScript("window.luma.prepare(" + JavaScriptString(source) + ",false," + (muted ? "true" : "false") + "," + request + "," + targetFps + ")");
            AppLog.Write("Media prepared in permanent host " + screen.DeviceName + " -> " + path);
        }

        private void ReportReady(int request)
        {
            if (request != mediaRequest || IsDisposed) return;
            browserReady = true;
            currentMediaPath = mediaPath;
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
            try { webView.CoreWebView2.ExecuteScriptAsync(script); } catch { }
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
            if (!playbackPaused || staticMode) return;

            DateTime now = DateTime.UtcNow;
            if ((now - lastMemoryMaintenance).TotalSeconds < MemoryMaintenanceSeconds) return;
            lastMemoryMaintenance = now;

            PurgeJavaScriptMemory();
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
        /// Sets this window's pause state and reports whether it actually changed.
        ///
        /// The return value lets the manager skip redundant work: ApplyPlaybackState
        /// pushes a script into the page, and doing that every health tick used to
        /// re-enter the video element and stall playback.
        /// </summary>
        public bool SetPaused(bool value)
        {
            if (playbackPaused == value) return false;
            playbackPaused = value;
            ApplyPlaybackState();
            ApplyMemoryTargetLevel();
            return true;
        }

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
                webView.CoreWebView2.MemoryUsageTargetLevel = playbackPaused
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
        /// Fire-and-forget by design. This runs on the pause path, and a wallpaper must
        /// never be held up waiting for the browser to answer a housekeeping call.
        /// </summary>
        private void RequestMemoryPressure()
        {
            if (staticMode) return;
            if (webView == null || webView.IsDisposed || webView.CoreWebView2 == null) return;
            try
            {
                webView.CoreWebView2.CallDevToolsProtocolMethodAsync("Memory.simulatePressureNotification",
                    "{\"level\":\"critical\"}");
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
                AppLog.Write("Wallpaper already active; reasserted " + screen.DeviceName + " -> " + path);
                return;
            }

            if (existing != null && existing.MatchesScreen(screen))
            {
                CancelPending(screen.DeviceName);
                existing.ChangeMedia(path, mute, fps);
                SyncPause(existing, screen.DeviceName);
                AppLog.Write("Wallpaper changed inside permanent host " + screen.DeviceName + " -> " + path);
                return;
            }

            WallpaperWindow preparing;
            if (pending.TryGetValue(screen.DeviceName, out preparing) && preparing.Matches(screen, path))
            {
                preparing.SetMute(mute);
                preparing.SetTargetFps(fps);
                SyncPause(preparing, screen.DeviceName);
                AppLog.Write("Wallpaper swap already preparing " + screen.DeviceName + " -> " + path);
                return;
            }

            CancelPending(screen.DeviceName);
            var window = new WallpaperWindow(screen, path, mute, fps);
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
