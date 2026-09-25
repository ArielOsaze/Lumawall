using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Shell;
using System.Windows.Threading;
using Polygon = System.Windows.Shapes.Polygon;
using Forms = System.Windows.Forms;
using Drawing = System.Drawing;
using Microsoft.Win32;
using Microsoft.Web.WebView2.Core;

namespace LumaWall
{
    internal sealed class MainWindow : Window
    {
        private static readonly Dictionary<string, string[]> Copy = new Dictionary<string, string[]>
        {
            { "nav.home", new[] { "Beranda", "Dashboard", "主页", "ホーム" } },
            { "nav.library", new[] { "Koleksi", "Library", "媒体库", "ライブラリ" } },
            { "nav.discover", new[] { "Katalog", "Catalog", "目录", "カタログ" } },
            { "nav.displays", new[] { "Monitor", "Displays", "显示器", "モニター" } },
            { "nav.performance", new[] { "Performa", "Performance", "性能", "パフォーマンス" } },
            { "home.title", new[] { "Beranda", "Dashboard", "主页", "ホーム" } },
            { "home.sub", new[] { "Pusat kendali wallpaper desktop.", "Control center for your desktop wallpaper.", "桌面壁纸控制中心。", "デスクトップ壁紙のコントロールセンター。" } },
            { "home.hero", new[] { "Wallpaper desktop", "Desktop wallpaper", "桌面壁纸", "デスクトップ壁紙" } },
            { "home.hero.sub", new[] { "Gunakan video atau gambar. Optimalkan video bila diperlukan.", "Use a video or image. Optimize video when needed.", "使用视频或图片，并按需优化视频。", "動画または画像を使用し、必要に応じて最適化します。" } },
            { "hero.featured", new[] { "SEDANG DIPILIH", "FEATURED", "精选", "注目" } },
            { "action.add", new[] { "Tambah wallpaper", "Add wallpaper", "添加壁纸", "壁紙を追加" } },
            { "action.add.short", new[] { "Tambah", "Add", "添加", "追加" } },
            { "action.catalog", new[] { "Buka katalog", "Open catalog", "打开目录", "カタログを開く" } },
            { "action.more", new[] { "Tampilkan lainnya", "Show more", "显示更多", "もっと見る" } },
            { "action.details", new[] { "Detail", "Details", "详情", "詳細" } },
            { "action.reload", new[] { "Muat ulang", "Reload", "重新加载", "再読み込み" } },
            { "metric.monitor", new[] { "Monitor", "Displays", "显示器", "モニター" } },
            { "metric.active", new[] { "Aktif", "Active", "使用中", "使用中" } },
            { "metric.library", new[] { "Koleksi", "Library", "媒体库", "ライブラリ" } },
            { "metric.catalog", new[] { "Katalog", "Catalog", "目录", "カタログ" } },
            { "recent", new[] { "Terakhir ditambahkan", "Recently added", "最近添加", "最近追加" } },
            { "picks", new[] { "Pilihan katalog", "Catalog picks", "目录精选", "カタログの注目" } },
            { "view.all", new[] { "Lihat semua", "View all", "查看全部", "すべて表示" } },
            { "empty.library", new[] { "Koleksi masih kosong", "Library is empty", "媒体库为空", "ライブラリは空です" } },
            { "empty.library.sub", new[] { "Tambahkan video atau gambar untuk mulai.", "Add a video or image to begin.", "添加视频或图片即可开始。", "動画または画像を追加してください。" } },
            { "empty.catalog", new[] { "Tidak ada hasil", "No results", "没有结果", "結果がありません" } },
            { "empty.catalog.sub", new[] { "Ubah pencarian atau kategori.", "Change the search or category.", "请更改搜索或分类。", "検索またはカテゴリを変更してください。" } },
            { "library.title", new[] { "Koleksi", "Library", "媒体库", "ライブラリ" } },
            { "library.none", new[] { "Pilih wallpaper untuk melihat tindakan.", "Select a wallpaper to see actions.", "选择壁纸以查看操作。", "壁紙を選択すると操作が表示されます。" } },
            { "action.optimize", new[] { "Optimalkan", "Optimize", "优化", "最適化" } },
            { "catalog.title", new[] { "Katalog", "Catalog", "目录", "カタログ" } },
            { "display.title", new[] { "Monitor", "Displays", "显示器", "モニター" } },
            { "display.sub", new[] { "Tetapkan wallpaper untuk setiap monitor.", "Assign a wallpaper to each display.", "为每台显示器设置壁纸。", "各モニターに壁紙を設定します。" } },
            { "display.pick", new[] { "Pilih wallpaper dari Koleksi terlebih dahulu.", "Select a wallpaper from Library first.", "请先从媒体库选择壁纸。", "先にライブラリから壁紙を選択してください。" } },
            { "display.selected", new[] { "Terpilih", "Selected", "已选择", "選択中" } },
            { "display.primary", new[] { "Utama", "Primary", "主显示器", "メイン" } },
            { "display.unset", new[] { "Belum diatur", "Not set", "未设置", "未設定" } },
            { "action.apply", new[] { "Terapkan", "Apply", "应用", "適用" } },
            { "action.stop", new[] { "Hentikan", "Stop", "停止", "停止" } },
            { "perf.title", new[] { "Performa", "Performance", "性能", "パフォーマンス" } },
            { "perf.sub", new[] { "Batasi penggunaan daya dan proses video.", "Control power use and video processing.", "控制功耗和视频处理。", "電力使用量と動画処理を調整します。" } },
            { "fps.title", new[] { "Batas frame rate", "Frame-rate limit", "帧率限制", "フレームレート上限" } },
            { "fps.sub", new[] { "Optimasi membuat salinan video sesuai FPS pilihan.", "Optimization creates a copy at the selected FPS.", "优化会按所选帧率创建视频副本。", "選択したFPSで最適化済みのコピーを作成します。" } },
            { "auto.title", new[] { "Pause otomatis", "Automatic pause", "自动暂停", "自動一時停止" } },
            { "auto.sub", new[] { "Hentikan pemutaran saat wallpaper tidak terlihat.", "Stop playback when the wallpaper is not visible.", "壁纸不可见时停止播放。", "壁紙が見えないときは再生を停止します。" } },
            { "check.fullscreen", new[] { "Saat aplikasi fullscreen", "While an app is fullscreen", "应用全屏时", "アプリが全画面のとき" } },
            { "check.maximized", new[] { "Saat aplikasi lain dimaksimalkan", "While another app is maximized", "其他应用最大化时", "他のアプリが最大化されたとき" } },
            { "check.battery", new[] { "Saat menggunakan baterai", "While running on battery", "使用电池时", "バッテリー使用時" } },
            { "check.mute", new[] { "Matikan audio wallpaper", "Mute wallpaper audio", "关闭壁纸声音", "壁紙の音声をミュート" } },
            { "check.startup", new[] { "Jalankan bersama Windows", "Start with Windows", "随 Windows 启动", "Windows起動時に実行" } },
            { "perf.note", new[] { "Video didekode di GPU (hardware decode), jadi CPU tetap rendah. 15 FPS paling hemat. 24 FPS cocok untuk sebagian besar loop. 30 FPS lebih halus.", "Video is decoded on the GPU (hardware decode), keeping CPU low. 15 FPS uses the least power. 24 FPS suits most loops. 30 FPS is smoother.", "视频由 GPU 硬件解码，CPU 占用低。15 FPS 最省电，24 FPS 适合大多数循环，30 FPS 更流畅。", "動画はGPUでハードウェアデコードされるためCPU負荷は低めです。15 FPSは省電力、24 FPSは多くのループ向け、30 FPSはより滑らかです。" } },
            { "perf.live", new[] { "Telemetri langsung", "Live telemetry", "实时监控", "ライブ計測" } },
            { "perf.live.sub", new[] { "Pemakaian mesin wallpaper saat ini.", "Current wallpaper engine usage.", "当前壁纸引擎占用。", "現在の壁紙エンジン使用量。" } },
            { "stat.cpu", new[] { "CPU", "CPU", "CPU", "CPU" } },
            { "stat.ram", new[] { "Memori", "Memory", "内存", "メモリ" } },
            { "stat.active", new[] { "Wallpaper aktif", "Active wallpapers", "活动壁纸", "稼働中の壁紙" } },
            { "toast.tray", new[] { "LumaWall tetap aktif di area notifikasi.", "LumaWall is still running in the notification area.", "LumaWall 仍在通知区域运行。", "LumaWall は通知領域で実行中です。" } },
            { "toast.fps", new[] { "Batas FPS", "FPS limit", "帧率限制", "FPS上限" } },
            { "rail.screens", new[] { "LAYAR", "SCREENS", "屏幕", "画面" } },
            { "toast.selected", new[] { "Terpilih", "Selected", "已选择", "選択中" } },
            { "toast.pick", new[] { "Pilih wallpaper terlebih dahulu.", "Select a wallpaper first.", "请先选择壁纸。", "先に壁紙を選択してください。" } },
            { "toast.noruntime", new[] { "WebView2 Runtime belum terpasang. Unduh gratis dari Microsoft, lalu jalankan ulang LumaWall.", "WebView2 Runtime is not installed. Download it free from Microsoft, then restart LumaWall.", "未安装 WebView2 运行时。请从 Microsoft 免费下载，然后重启 LumaWall。", "WebView2 ランタイムがインストールされていません。Microsoft から無料でダウンロードし、LumaWall を再起動してください。" } },
            { "toast.monitor", new[] { "Monitor tidak tersedia.", "Display is unavailable.", "显示器不可用。", "モニターを利用できません。" } },
            { "toast.applied", new[] { "Wallpaper diterapkan.", "Wallpaper applied.", "壁纸已应用。", "壁紙を適用しました。" } },
            { "toast.stopped", new[] { "Wallpaper dihentikan.", "Wallpaper stopped.", "壁纸已停止。", "壁紙を停止しました。" } },
            { "toast.video", new[] { "Pilih video terlebih dahulu.", "Select a video first.", "请先选择视频。", "先に動画を選択してください。" } },
            { "toast.static", new[] { "Wallpaper statis tidak perlu optimasi FPS.", "Static wallpapers do not need FPS optimization.", "静态壁纸无需帧率优化。", "静止画はFPS最適化が不要です。" } },
            { "toast.ffmpeg", new[] { "FFmpeg tidak ditemukan.", "FFmpeg was not found.", "未找到 FFmpeg。", "FFmpeg が見つかりません。" } },
            { "toast.optimizing", new[] { "Mengoptimalkan", "Optimizing", "正在优化", "最適化中" } },
            { "toast.ready", new[] { "Versi optimal siap digunakan.", "Optimized version is ready.", "优化版本已准备就绪。", "最適化版を使用できます。" } },
            { "toast.failed", new[] { "Optimasi gagal.", "Optimization failed.", "优化失败。", "最適化に失敗しました。" } },
            { "toast.catalog", new[] { "Katalog dimuat.", "Catalog loaded.", "目录已加载。", "カタログを読み込みました。" } },
            { "toast.cataloging", new[] { "Memuat katalog…", "Loading catalog…", "正在加载目录…", "カタログを読み込み中…" } },
            { "toast.downloading", new[] { "Mengunduh", "Downloading", "正在下载", "ダウンロード中" } },
            { "mature.title", new[] { "Konten dewasa", "Mature content", "成人内容", "成人向けコンテンツ" } },
            { "mature.warning", new[] { "Kategori ini berisi ilustrasi sugestif non-eksplisit untuk pengguna berusia 18 tahun ke atas. Lanjutkan?", "This category contains non-explicit suggestive artwork intended for users aged 18 and over. Continue?", "此分类包含面向18岁以上用户的非露骨成人向插画。是否继续？", "このカテゴリには18歳以上を対象とした、露骨ではない成人向けイラストが含まれます。続行しますか？" } },
            { "action.continue", new[] { "Saya berusia 18+", "I am 18 or older", "我已年满18岁", "18歳以上です" } },
            { "action.cancel", new[] { "Batal", "Cancel", "取消", "キャンセル" } },
            { "catalog.search", new[] { "Cari wallpaper, karakter, atau suasana", "Search wallpapers, characters, or moods", "搜索壁纸、角色或风格", "壁紙・キャラクター・雰囲気を検索" } },
            { "catalog.details", new[] { "Detail wallpaper", "Wallpaper details", "壁纸详情", "壁紙の詳細" } },
            { "catalog.download", new[] { "Unduh & terapkan", "Download & apply", "下载并应用", "ダウンロードして適用" } },
            { "catalog.source", new[] { "Lihat sumber", "View source", "查看来源", "配布元を見る" } },
            { "profile.title", new[] { "Profil multi-monitor", "Multi-display profiles", "多显示器配置", "マルチモニタープロファイル" } },
            { "profile.save", new[] { "Simpan profil", "Save profile", "保存配置", "プロファイルを保存" } },
            { "profile.name", new[] { "Nama profil", "Profile name", "配置名称", "プロファイル名" } },
            { "apply.choose", new[] { "Pilih layar tujuan", "Choose a display", "选择目标显示器", "表示先を選択" } },
            { "apply.all", new[] { "Semua monitor", "All displays", "所有显示器", "すべてのモニター" } },
            { "apply.screens", new[] { "layar", "displays", "台显示器", "台のモニター" } },
            { "apply.together", new[] { "Terapkan serentak", "Apply together", "同时应用", "一括で適用" } },
            { "apply.hint", new[] { "Satu klik langsung menerapkan wallpaper. Pilihan tersimpan otomatis.", "One click applies the wallpaper. Your choice is saved automatically.", "单击即可应用壁纸，选择会自动保存。", "ワンクリックで壁紙を適用し、選択内容を自動保存します。" } },
            { "action.download", new[] { "Unduh", "Download", "下载", "ダウンロード" } },
            { "library.selected", new[] { "Wallpaper terpilih", "Selected wallpaper", "已选壁纸", "選択中の壁紙" } },
            { "library.ready", new[] { "Siap diterapkan", "Ready to apply", "可以应用", "適用できます" } },
            { "library.items", new[] { "Wallpaper Anda", "Your wallpapers", "你的壁纸", "あなたの壁紙" } },
            { "catalog.browse", new[] { "Jelajahi wallpaper", "Browse wallpapers", "浏览壁纸", "壁紙を探す" } },
            { "catalog.collection", new[] { "Kategori", "Categories", "分类", "カテゴリー" } },
            { "status.audio.off", new[] { "Audio mati", "Audio off", "音频关闭", "音声オフ" } },
            { "status.audio.on", new[] { "Audio hidup", "Audio on", "音频开启", "音声オン" } },
            { "status.wallpaper", new[] { "Wallpaper", "Wallpaper", "壁纸", "壁紙" } },
            { "inspector.output", new[] { "Target monitor", "Display target", "显示目标", "表示先" } },
            { "inspector.detected", new[] { "terdeteksi", "detected", "已检测", "検出" } }
        };

        private readonly ConfigStore store = new ConfigStore();
        private readonly AppConfig config;
        private readonly WallpaperManager manager = new WallpaperManager();
        private ContentControl pageHost;
        private readonly Dictionary<string, Button> navButtons = new Dictionary<string, Button>();
        private readonly Dictionary<string, TextBlock> navLabels = new Dictionary<string, TextBlock>();
        private readonly Dictionary<string, Border> navAccents = new Dictionary<string, Border>();
        private readonly List<CatalogItem> catalogItems = new List<CatalogItem>();
        private readonly Dictionary<CatalogItem, Border> catalogCardViews = new Dictionary<CatalogItem, Border>();
        private readonly DispatcherTimer healthTimer = new DispatcherTimer();
        private TextBlock toastText;
        private Border toast;
        private TextBlock statusWallpaperText;
        private TextBlock statusTelemetryText;
        private TextBlock searchWatermark;
        private TextBox searchBox;
        private Forms.NotifyIcon tray;
        private string activePage = "discover";
        private string selectedVideo;
        private CatalogItem selectedCatalogItem;
        private string selectedMonitor;
        private string activeCategory = "Semua";
        private string catalogSearch = "";
        private int catalogVisibleCount = 24;
        private string lastMonitorSignature;
        private int catalogLayoutBucket = -1;
        private ScrollViewer catalogGalleryScroll;
        private bool userPaused;
        private bool systemIdle;
        private bool exiting;
        private readonly bool startHidden;
        private ContentControl catalogInspectorHost;
        private TextBlock telemetryCpu;
        private TextBlock telemetryRam;
        private TextBlock telemetryActive;
        private TimeSpan lastCpuTime;
        private DateTime lastCpuStamp = DateTime.MinValue;

        // Gamer palette: deep space black, crimson primary, cyan accent.
        private static readonly Color CWindow = Color.FromRgb(7, 8, 11);
        private static readonly Color CSidebar = Color.FromRgb(10, 12, 16);
        private static readonly Color CSurface = Color.FromRgb(16, 19, 26);
        private static readonly Color CSurface2 = Color.FromRgb(22, 26, 35);
        private static readonly Color CSurfaceHover = Color.FromRgb(31, 37, 50);
        private static readonly Color CBorder = Color.FromRgb(34, 40, 52);
        private static readonly Color CBorderHot = Color.FromRgb(60, 68, 86);
        private static readonly Color CPrimary = Color.FromRgb(255, 46, 67);
        private static readonly Color CPrimaryHi = Color.FromRgb(255, 96, 116);
        private static readonly Color CPrimarySoft = Color.FromRgb(46, 13, 21);
        private static readonly Color CAccent = Color.FromRgb(34, 211, 238);
        private static readonly Color CAccentSoft = Color.FromRgb(10, 40, 48);
        private static readonly Color CWarning = Color.FromRgb(250, 184, 72);
        private static readonly Color CText = Color.FromRgb(242, 245, 250);
        private static readonly Color CMuted = Color.FromRgb(154, 163, 181);
        private static readonly Color CDim = Color.FromRgb(116, 125, 143);
        private static readonly FontFamily FDisplay = new FontFamily("Bahnschrift SemiBold, Bahnschrift, Segoe UI");
        private static readonly FontFamily FMono = new FontFamily("Cascadia Mono, Consolas, Courier New");
        private const int WmGetMinMaxInfo = 0x0024;
        private const int WmWtssessionChange = 0x02B1;
        private const int WtsSessionLock = 0x7;
        private const int WtsSessionUnlock = 0x8;
        private const int WmPowerBroadcast = 0x0218;
        private const int PbtApmresume = 0x0007;
        private const int PbtApmsuspend = 0x0004;
        private const int PbtPowersettingchange = 0x8013;
        private const uint MonitorDefaultToNearest = 0x00000002;

        [StructLayout(LayoutKind.Sequential)]
        private struct PowerBroadcastSetting
        {
            public Guid PowerSetting;
            public uint DataLength;
            public byte Data;
        }

        /// <summary>GUID_CONSOLE_DISPLAY_STATE - sent when the monitor turns on/off.</summary>
        private static readonly Guid GuidConsoleDisplayState = new Guid("6FE69556-704A-47A0-8F24-C28D936FDA47");

        [StructLayout(LayoutKind.Sequential)]
        private struct NativePoint { public int X; public int Y; }

        [StructLayout(LayoutKind.Sequential)]
        private struct NativeMinMaxInfo
        {
            public NativePoint Reserved;
            public NativePoint MaxSize;
            public NativePoint MaxPosition;
            public NativePoint MinTrackSize;
            public NativePoint MaxTrackSize;
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
        private struct NativeMonitorInfo
        {
            public int Size;
            public NativeRect Monitor;
            public NativeRect Work;
            public uint Flags;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct NativeRect { public int Left, Top, Right, Bottom; }

        [DllImport("user32.dll")]
        private static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint flags);

        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        private static extern bool GetMonitorInfo(IntPtr monitor, ref NativeMonitorInfo info);

        // --- instant foreground tracking ------------------------------------
        // The health timer polls every 2 s, so leaving a fullscreen app could take
        // up to 2 s before the wallpaper resumed - very visible. A WinEvent hook
        // fires the moment the foreground window changes, so the wallpaper starts
        // again immediately.
        //
        // The range must include OBJECT_DESTROY/HIDE: a game that is closed rather
        // than minimized sends no FOREGROUND event (the desktop was already behind
        // it), so watching only the foreground events left the wallpaper paused
        // until something else happened to wake the app up - the "wallpaper only
        // starts after I click" bug.
        private const uint EventSystemForeground = 0x0003;
        private const uint EventObjectDestroy = 0x8001;
        private const uint EventObjectHide = 0x8003;
        private const uint EventObjectShow = 0x8002;
        private const uint EventSystemMinimizeStart = 0x0016;
        private const uint EventSystemMinimizeEnd = 0x0017;
        private const uint WmEventOutOfContext = 0x0000;

        private delegate void WinEventDelegate(IntPtr hook, uint eventType, IntPtr hwnd,
            int idObject, int idChild, uint thread, uint time);

        [DllImport("user32.dll")]
        private static extern IntPtr SetWinEventHook(uint eventMin, uint eventMax, IntPtr module,
            WinEventDelegate callback, uint processId, uint threadId, uint flags);

        [DllImport("user32.dll")]
        private static extern bool UnhookWinEvent(IntPtr hook);

        private IntPtr foregroundHook;
        private IntPtr objectHook;
        // Keeps the delegate alive: the GC would otherwise collect it while the
        // native side still holds the pointer, crashing on the next event.
        private WinEventDelegate foregroundCallback;
        // True while a coalesced pause evaluation is already queued.
        private bool pauseEvaluationPending;

        public MainWindow()
        {
            config = store.Load();
            if (config.DisplayProfiles == null) config.DisplayProfiles = new Dictionary<string, Dictionary<string, string>>();
            startHidden = Environment.GetCommandLineArgs().Any(x => string.Equals(x, "--background", StringComparison.OrdinalIgnoreCase));
            config.StartWithWindows = IsStartupEnabled();
            if (config.TargetFps != 15 && config.TargetFps != 24 && config.TargetFps != 30) config.TargetFps = 24;
            if (config.Language != "id" && config.Language != "en" && config.Language != "zh" && config.Language != "ja") config.Language = "id";
            foreach (string argument in Environment.GetCommandLineArgs())
            {
                if (argument == "--lang=id") config.Language = "id";
                else if (argument == "--lang=en") config.Language = "en";
                else if (argument == "--lang=zh") config.Language = "zh";
                else if (argument == "--lang=ja") config.Language = "ja";
            }
            Title = "LumaWall";
            WindowStartupLocation = WindowStartupLocation.CenterScreen;
            MinWidth = 920;
            MinHeight = 580;
            Rect workArea = SystemParameters.WorkArea;
            Width = Math.Max(MinWidth, Math.Min(1580, workArea.Width - 20));
            Height = Math.Max(MinHeight, Math.Min(950, workArea.Height - 20));
            WindowStyle = WindowStyle.None;
            ResizeMode = ResizeMode.CanResize;
            if (startHidden)
            {
                ShowActivated = false;
                ShowInTaskbar = false;
                WindowState = WindowState.Minimized;
            }
            Background = new SolidColorBrush(CWindow);
            Foreground = new SolidColorBrush(CText);
            FontFamily = new FontFamily("Segoe UI Variable Text, Segoe UI");
            TextOptions.SetTextFormattingMode(this, TextFormattingMode.Display);
            TextOptions.SetTextRenderingMode(this, TextRenderingMode.ClearType);
            WindowChrome.SetWindowChrome(this, new WindowChrome
            {
                CaptionHeight = 0,
                ResizeBorderThickness = new Thickness(7),
                CornerRadius = new CornerRadius(14),
                GlassFrameThickness = new Thickness(0),
                UseAeroCaptionButtons = false
            });
            Content = BuildShell();
            Loaded += OnLoaded;
            SizeChanged += OnWindowSizeChanged;
            Closing += OnClosing;
            SetupTray();
            healthTimer.Interval = TimeSpan.FromSeconds(2);
            healthTimer.Tick += OnHealthTick;
        }

        protected override void OnSourceInitialized(EventArgs e)
        {
            base.OnSourceInitialized(e);
            HwndSource source = HwndSource.FromHwnd(new WindowInteropHelper(this).Handle);
            if (source != null) source.AddHook(WindowMessageHook);
            InstallForegroundHook();
        }

        /// <summary>
        /// Watches foreground/minimize changes so the pause state reacts the
        /// instant the user leaves a fullscreen app, instead of waiting for the
        /// next 2-second health tick.
        /// </summary>
        private void InstallForegroundHook()
        {
            if (foregroundHook != IntPtr.Zero) return;
            foregroundCallback = delegate(IntPtr hook, uint eventType, IntPtr hwnd,
                int idObject, int idChild, uint thread, uint time)
            {
                // The callback arrives on this thread's message pump, but a
                // non-child window may already be gone; ApplyPauseState tolerates
                // that and is cheap, so it is safe to call directly.
                //
                // Events arrive in bursts (closing a window fires DESTROY plus
                // several HIDE/SHOW pairs). Recomputing on each one would hammer
                // the pause path, so the work is coalesced onto one dispatcher
                // tick: the first event schedules the evaluation, the rest are
                // absorbed while it is pending.
                try { SchedulePauseEvaluation(); } catch { }
            };
            // Two ranges are needed because WinEventHook takes a single
            // [min,max] span and the events we care about are far apart:
            //   0x0003..0x0017 - foreground changes and minimize transitions
            //   0x8001..0x8003 - object destroy / show / hide
            foregroundHook = SetWinEventHook(
                EventSystemForeground, EventSystemMinimizeEnd,
                IntPtr.Zero, foregroundCallback, 0, 0, WmEventOutOfContext);
            objectHook = SetWinEventHook(
                EventObjectDestroy, EventObjectHide,
                IntPtr.Zero, foregroundCallback, 0, 0, WmEventOutOfContext);
            if (foregroundHook == IntPtr.Zero || objectHook == IntPtr.Zero)
                AppLog.Write("Foreground hook partially unavailable; the 2s poll still covers it");
        }

        /// <summary>
        /// Coalesces a burst of shell events into a single pause evaluation.
        ///
        /// Without this, closing a game triggers several events in a few
        /// milliseconds and each one would re-scan every window.
        ///
        /// The priority matters for how it feels. DispatcherPriority.Background
        /// is the lowest useful priority, so the evaluation waited behind every
        /// other queued UI operation - measured at ~400 ms of visible delay
        /// before the wallpaper actually stopped. Input-level priority runs
        /// ahead of layout and rendering work, which is what "immediate" means
        /// here: the wallpaper stops while the window is still appearing.
        /// </summary>
        private void SchedulePauseEvaluation()
        {
            if (pauseEvaluationPending) return;
            pauseEvaluationPending = true;
            Dispatcher.BeginInvoke(new Action(delegate
            {
                pauseEvaluationPending = false;
                ApplyPauseState();
            }), DispatcherPriority.Input);
        }

        private void RemoveForegroundHook()
        {
            if (foregroundHook != IntPtr.Zero)
            {
                try { UnhookWinEvent(foregroundHook); } catch { }
                foregroundHook = IntPtr.Zero;
            }
            if (objectHook != IntPtr.Zero)
            {
                try { UnhookWinEvent(objectHook); } catch { }
                objectHook = IntPtr.Zero;
            }
            foregroundCallback = null;
        }

        private IntPtr WindowMessageHook(IntPtr hwnd, int message, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            // Session lock / display-off. While the session is locked or the
            // monitor is asleep the wallpaper is not visible at all, so pausing
            // the decoders costs nothing visually but stops ~20% of GPU video
            // decode on a three-monitor setup. Resume puts it straight back.
            if (message == WmWtssessionChange)
            {
                int change = wParam.ToInt32();
                if (change == WtsSessionLock) SetSystemIdle(true);
                else if (change == WtsSessionUnlock) SetSystemIdle(false);
                return IntPtr.Zero;
            }
            if (message == WmPowerBroadcast)
            {
                int powerEvent = wParam.ToInt32();
                if (powerEvent == PbtApmsuspend) SetSystemIdle(true);
                else if (powerEvent == PbtApmresume) SetSystemIdle(false);
                else if (powerEvent == PbtPowersettingchange)
                {
                    // lParam points at a POWERBROADCAST_SETTING, not a value:
                    // reading it directly gave the pointer, so this never fired.
                    // Only the console-display-state setting is relevant here
                    // (0 = off, 1 = on, 2 = dimmed); other settings are ignored.
                    try
                    {
                        var setting = (PowerBroadcastSetting)Marshal.PtrToStructure(lParam, typeof(PowerBroadcastSetting));
                        if (setting.PowerSetting == GuidConsoleDisplayState)
                        {
                            if (setting.Data == 0 || setting.Data == 2) SetSystemIdle(true);
                            else if (setting.Data == 1) SetSystemIdle(false);
                        }
                    }
                    catch { }
                }
                return IntPtr.Zero;
            }

            if (message != WmGetMinMaxInfo) return IntPtr.Zero;
            var info = (NativeMinMaxInfo)Marshal.PtrToStructure(lParam, typeof(NativeMinMaxInfo));
            IntPtr monitor = MonitorFromWindow(hwnd, MonitorDefaultToNearest);
            if (monitor != IntPtr.Zero)
            {
                var monitorInfo = new NativeMonitorInfo { Size = Marshal.SizeOf(typeof(NativeMonitorInfo)) };
                if (GetMonitorInfo(monitor, ref monitorInfo))
                {
                    info.MaxPosition.X = Math.Abs(monitorInfo.Work.Left - monitorInfo.Monitor.Left);
                    info.MaxPosition.Y = Math.Abs(monitorInfo.Work.Top - monitorInfo.Monitor.Top);
                    info.MaxSize.X = Math.Abs(monitorInfo.Work.Right - monitorInfo.Work.Left);
                    info.MaxSize.Y = Math.Abs(monitorInfo.Work.Bottom - monitorInfo.Work.Top);
                    Marshal.StructureToPtr(info, lParam, true);
                    handled = true;
                }
            }
            return IntPtr.Zero;
        }

        private string Tr(string key)
        {
            string[] values;
            if (!Copy.TryGetValue(key, out values)) return key;
            int index = config.Language == "en" ? 1 : config.Language == "zh" ? 2 : config.Language == "ja" ? 3 : 0;
            return values[index];
        }

        private string CategoryLabel(string value)
        {
            if (config.Language == "id")
            {
                if (value == "All" || value == "Semua") return "Semua";
                if (value == "Nature") return "Alam";
                if (value == "Space") return "Antariksa";
                if (value == "City") return "Kota";
                if (value == "Architecture") return "Arsitektur";
                if (value == "Anime Girls") return "Anime perempuan";
                if (value == "Anime Loop") return "Anime bergerak";
                if (value == "Dynamic") return "Dinamis";
                if (value == "Mature 18+") return "Dewasa 18+";
            }
            else if (config.Language == "zh")
            {
                if (value == "All" || value == "Semua") return "全部";
                if (value == "Nature") return "自然";
                if (value == "Space") return "太空";
                if (value == "City") return "城市";
                if (value == "Architecture") return "建筑";
                if (value == "Abstract") return "抽象";
                if (value == "Anime-style") return "动漫风格";
                if (value == "Anime Girls") return "动漫女孩";
                if (value == "Anime Loop") return "动漫动态";
                if (value == "Dynamic") return "动态";
                if (value == "Mature 18+") return "成人 18+";
            }
            else if (config.Language == "ja")
            {
                if (value == "All" || value == "Semua") return "すべて";
                if (value == "Nature") return "自然";
                if (value == "Space") return "宇宙";
                if (value == "City") return "都市";
                if (value == "Architecture") return "建築";
                if (value == "Abstract") return "抽象";
                if (value == "Anime-style") return "アニメ風";
                if (value == "Anime Girls") return "アニメ女性";
                if (value == "Anime Loop") return "アニメ動画";
                if (value == "Dynamic") return "動画";
                if (value == "Mature 18+") return "成人向け 18+";
            }
            else if (value == "Semua") return "All";
            return value;
        }

        // ================= SHELL =================

        private UIElement BuildShell()
        {
            pageHost = new ContentControl();
            toastText = new TextBlock();
            catalogInspectorHost = null;
            catalogCardViews.Clear();
            navButtons.Clear();
            navLabels.Clear();
            navAccents.Clear();

            // Native scrollbars are used on purpose: custom templated scrollbars
            // built from nested FrameworkElementFactory trees crash WPF's template
            // sealer at runtime, and a wallpaper app must never fault on layout.
            var root = new Grid { Background = new SolidColorBrush(CWindow) };
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(54) });
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(30) });
            root.Children.Add(BuildTitleBar());

            var body = new Grid();
            body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(92) });
            body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            body.Children.Add(BuildNavRail());
            pageHost.Background = new SolidColorBrush(CWindow);
            Grid.SetColumn(pageHost, 1);
            body.Children.Add(pageHost);
            Grid.SetRow(body, 1);
            root.Children.Add(body);

            var status = new Grid { Background = new SolidColorBrush(Color.FromRgb(9, 10, 14)) };
            status.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            status.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var leftStatus = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(16, 0, 0, 0) };
            leftStatus.Children.Add(new Border
            {
                Width = 7,
                Height = 7,
                CornerRadius = new CornerRadius(4),
                Background = new SolidColorBrush(CAccent),
                VerticalAlignment = VerticalAlignment.Center,
                Effect = new DropShadowEffect { Color = CAccent, BlurRadius = 9, ShadowDepth = 0, Opacity = .85 }
            });
            string current = config.MonitorVideos.Values.FirstOrDefault(File.Exists);
            statusWallpaperText = new TextBlock
            {
                Text = current == null ? Tr("display.unset") : Path.GetFileNameWithoutExtension(current),
                Foreground = new SolidColorBrush(CMuted),
                FontSize = 10.5,
                Margin = new Thickness(9, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
                MaxWidth = 520
            };
            leftStatus.Children.Add(statusWallpaperText);
            status.Children.Add(leftStatus);
            statusTelemetryText = new TextBlock
            {
                Text = Forms.Screen.AllScreens.Length + " " + Tr("apply.screens") + "   ·   " + config.TargetFps + " FPS   ·   " + Tr(config.Mute ? "status.audio.off" : "status.audio.on"),
                Foreground = new SolidColorBrush(CDim),
                FontFamily = FMono,
                FontSize = 10,
                Margin = new Thickness(0, 0, 18, 0),
                VerticalAlignment = VerticalAlignment.Center
            };
            Grid.SetColumn(statusTelemetryText, 1);
            status.Children.Add(statusTelemetryText);
            Grid.SetRow(status, 2);
            root.Children.Add(status);

            toastText.Foreground = new SolidColorBrush(CText);
            toastText.FontSize = 12.5;
            toastText.VerticalAlignment = VerticalAlignment.Center;
            toast = new Border
            {
                Background = new SolidColorBrush(Color.FromRgb(20, 24, 32)),
                BorderBrush = new SolidColorBrush(CPrimary),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(8),
                Padding = new Thickness(18, 12, 18, 12),
                Child = toastText,
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Bottom,
                Margin = new Thickness(0, 0, 26, 26),
                Visibility = Visibility.Collapsed,
                Effect = new DropShadowEffect { Color = Colors.Black, BlurRadius = 22, ShadowDepth = 5, Opacity = .55 }
            };
            Grid.SetRow(toast, 1);
            root.Children.Add(toast);
            return root;
        }

        private UIElement BuildTitleBar()
        {
            var bar = new Grid { Background = new SolidColorBrush(CSidebar) };
            bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(92) });
            bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            bar.MouseLeftButtonDown += delegate(object sender, MouseButtonEventArgs e)
            {
                if (e.ChangedButton != MouseButton.Left) return;
                if (e.ClickCount == 2) WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
                else DragMove();
            };

            var brand = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
            brand.Children.Add(BuildLogoMark(26));
            bar.Children.Add(brand);

            var middle = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(18, 0, 18, 0) };
            middle.Children.Add(new TextBlock { Text = "LUMAWALL", Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 13, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center });
            var versionBadge = new Border
            {
                Background = new SolidColorBrush(CPrimarySoft),
                BorderBrush = new SolidColorBrush(CPrimary),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(3),
                Padding = new Thickness(6, 2, 6, 2),
                Margin = new Thickness(9, 0, 18, 0),
                VerticalAlignment = VerticalAlignment.Center
            };
            versionBadge.Child = new TextBlock { Text = "4.0", Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 9, FontWeight = FontWeights.Bold };
            middle.Children.Add(versionBadge);

            var searchHost = new Grid { Width = 360, VerticalAlignment = VerticalAlignment.Center };
            searchBox = new TextBox
            {
                Text = catalogSearch,
                Height = 32,
                Padding = new Thickness(36, 7, 30, 6),
                FontSize = 12,
                Foreground = new SolidColorBrush(CText),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                CaretBrush = new SolidColorBrush(CPrimary)
            };
            searchHost.Children.Add(searchBox);
            var searchIcon = Glyph("\uE721", 12, new SolidColorBrush(CMuted));
            searchIcon.HorizontalAlignment = HorizontalAlignment.Left;
            searchIcon.Margin = new Thickness(12, 0, 0, 0);
            searchIcon.IsHitTestVisible = false;
            searchHost.Children.Add(searchIcon);
            searchWatermark = new TextBlock
            {
                Text = Tr("catalog.search"),
                Foreground = new SolidColorBrush(CDim),
                FontSize = 11.5,
                Margin = new Thickness(34, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center,
                IsHitTestVisible = false,
                Visibility = string.IsNullOrEmpty(catalogSearch) ? Visibility.Visible : Visibility.Collapsed
            };
            searchHost.Children.Add(searchWatermark);
            searchBox.TextChanged += delegate { searchWatermark.Visibility = string.IsNullOrEmpty(searchBox.Text) ? Visibility.Visible : Visibility.Collapsed; };
            searchBox.KeyDown += delegate(object sender, KeyEventArgs e)
            {
                if (e.Key != Key.Enter) return;
                catalogSearch = searchBox.Text.Trim();
                catalogVisibleCount = 30;
                SwitchPage("discover");
            };
            middle.Children.Add(searchHost);
            Grid.SetColumn(middle, 1);
            bar.Children.Add(middle);

            var right = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 6, 0) };
            var addButton = PrimaryButton(Icons.Add, Tr("action.add.short"));
            addButton.Height = 32;
            addButton.Margin = new Thickness(0, 0, 12, 0);
            addButton.Click += AddLocalVideo;
            right.Children.Add(addButton);

            string[] languageCodes = { "id", "en", "zh", "ja" };
            string[] languageLabels = { "ID", "EN", "中", "日" };
            var langGroup = new Border
            {
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(2),
                Margin = new Thickness(0, 0, 12, 0),
                VerticalAlignment = VerticalAlignment.Center
            };
            var langStack = new StackPanel { Orientation = Orientation.Horizontal };
            for (int languageIndex = 0; languageIndex < languageCodes.Length; languageIndex++)
            {
                string languageCode = languageCodes[languageIndex];
                bool active = config.Language == languageCode;
                var language = new Button
                {
                    Content = languageLabels[languageIndex],
                    Tag = languageCode,
                    Width = 28,
                    Height = 24,
                    Margin = new Thickness(1, 0, 1, 0),
                    Foreground = new SolidColorBrush(active ? Colors.White : CMuted),
                    Background = new SolidColorBrush(active ? CPrimary : Colors.Transparent),
                    BorderThickness = new Thickness(0),
                    Cursor = Cursors.Hand,
                    FontSize = 9.5,
                    FontWeight = FontWeights.SemiBold
                };
                SetRoundedButton(language, 3);
                language.Click += delegate(object sender, RoutedEventArgs e)
                {
                    config.Language = (string)((Button)sender).Tag;
                    store.Save(config);
                    string page = activePage;
                    Content = BuildShell();
                    SwitchPage(page);
                };
                langStack.Children.Add(language);
            }
            langGroup.Child = langStack;
            right.Children.Add(langGroup);

            var min = TitleButton("\uE921");
            System.Windows.Automation.AutomationProperties.SetName(min, "Minimize");
            min.Click += delegate { WindowState = WindowState.Minimized; };

            // The maximize button shows the "restore" glyph while the window is
            // maximized, matching every other Windows title bar. Without the
            // state swap the button keeps offering "maximize" on an already
            // maximized window.
            var max = TitleButton("\uE922");
            System.Windows.Automation.AutomationProperties.SetName(max, "Maximize");
            max.Click += delegate { WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized; };
            StateChanged += delegate
            {
                bool maximized = WindowState == WindowState.Maximized;
                max.Content = Icons.Build(maximized ? Icons.Restore : Icons.Maximize, 11, new SolidColorBrush(CMuted));
                System.Windows.Automation.AutomationProperties.SetName(max, maximized ? "Restore" : "Maximize");
            };

            var close = TitleButton("\uE8BB", isClose: true);
            System.Windows.Automation.AutomationProperties.SetName(close, "Close to tray");
            close.Click += delegate { Hide(); ShowToast(Tr("toast.tray")); };
            right.Children.Add(min);
            right.Children.Add(max);
            right.Children.Add(close);
            Grid.SetColumn(right, 2);
            bar.Children.Add(right);
            return bar;
        }

        private UIElement BuildNavRail()
        {
            var rail = new Grid { Background = new SolidColorBrush(CSidebar) };
            rail.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            rail.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var nav = new StackPanel { Margin = new Thickness(0, 12, 0, 0) };
            nav.Children.Add(NavRailButton("home", Icons.Dashboard, "nav.home"));
            nav.Children.Add(NavRailButton("library", Icons.Library, "nav.library"));
            nav.Children.Add(NavRailButton("discover", Icons.Catalog, "nav.discover"));
            nav.Children.Add(NavRailButton("displays", Icons.Displays, "nav.displays"));
            nav.Children.Add(NavRailButton("performance", Icons.Performance, "nav.performance"));
            rail.Children.Add(nav);

            var footer = new StackPanel { Margin = new Thickness(0, 0, 0, 14) };
            var engine = new Border
            {
                Width = 66,
                Margin = new Thickness(13, 0, 13, 10),
                Padding = new Thickness(0, 9, 0, 8),
                CornerRadius = new CornerRadius(7),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1)
            };
            // A bare "3 / 24 FPS" read as "3 FPS", which looked like a performance
            // bug. Label each number so the rail states what it means.
            var engineStack = new StackPanel();
            engineStack.Children.Add(new TextBlock { Text = Forms.Screen.AllScreens.Length.ToString(), Foreground = new SolidColorBrush(CAccent), FontFamily = FMono, FontSize = 17, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center });
            engineStack.Children.Add(new TextBlock { Text = Tr("rail.screens"), Foreground = new SolidColorBrush(CMuted), FontSize = 8, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 1, 0, 0) });
            engineStack.Children.Add(new TextBlock { Text = config.TargetFps + " FPS", Foreground = new SolidColorBrush(CDim), FontFamily = FMono, FontSize = 8.5, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 4, 0, 0) });
            engine.Child = engineStack;
            footer.Children.Add(engine);
            footer.Children.Add(new TextBlock { Text = "v4.0.0", Foreground = new SolidColorBrush(CDim), FontSize = 8.5, HorizontalAlignment = HorizontalAlignment.Center });
            Grid.SetRow(footer, 1);
            rail.Children.Add(footer);
            return rail;
        }

        private Button NavRailButton(string key, string iconName, string labelKey)
        {
            var content = new Grid { Width = 68, Height = 58 };
            var accent = new Border
            {
                Width = 3,
                CornerRadius = new CornerRadius(2),
                Background = new SolidColorBrush(CPrimary),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Stretch,
                Margin = new Thickness(0, 13, 0, 13),
                Visibility = Visibility.Collapsed,
                Effect = new DropShadowEffect { Color = CPrimary, BlurRadius = 10, ShadowDepth = 0, Opacity = .9 }
            };
            content.Children.Add(accent);
            var stack = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
            stack.Children.Add(Icons.Build(iconName, 19, new SolidColorBrush(CMuted)));
            var label = new TextBlock { Text = Tr(labelKey), Foreground = new SolidColorBrush(CMuted), FontSize = 9, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(2, 6, 2, 0), TextTrimming = TextTrimming.CharacterEllipsis };
            stack.Children.Add(label);
            content.Children.Add(stack);

            var button = new Button
            {
                Tag = key,
                Content = content,
                Width = 68,
                Height = 58,
                Margin = new Thickness(12, 3, 12, 3),
                Background = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand
            };
            System.Windows.Automation.AutomationProperties.SetName(button, Tr(labelKey));
            button.Click += delegate { SwitchPage(key); };
            button.MouseEnter += delegate { if (activePage != key) button.Background = new SolidColorBrush(CSurface); };
            button.MouseLeave += delegate { UpdateNav(); };
            SetRoundedButton(button, 10);
            navLabels[key] = label;
            navAccents[key] = accent;
            navButtons[key] = button;
            return button;
        }

        private Button TitleButton(string glyph, bool isClose = false)
        {
            // The title-bar buttons need their own template, for the same reason
            // the rest of the app's buttons do: WPF's default Button style carries
            // an Aero hover trigger that paints the button #FFBEE6FD - a pale blue
            // that has nothing to do with this app's palette. Setting Background
            // in code does not override it, because the template's trigger wins.
            //
            // The symptom was a light blue rectangle appearing over whichever
            // title-bar button the pointer happened to be on, which looked like a
            // rendering fault in every screenshot.
            var b = new Button
            {
                Width = 44,
                Height = 54,
                Content = Icons.Build(IconNameFor(glyph), 11, new SolidColorBrush(CMuted)),
                Background = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand
            };
            SetRoundedButton(b, 0);

            // Hover: a neutral lift, matching the rest of the chrome. Close gets
            // the conventional red, which is the one place a strong colour on this
            // bar is expected.
            var hover = isClose ? CPrimary : CSurface2;
            b.MouseEnter += delegate { b.Background = new SolidColorBrush(hover); };
            b.MouseLeave += delegate { b.Background = Brushes.Transparent; };

            // The icon has to lift with the background or it disappears into it.
            // Icons.Build returns a Canvas of Paths, so it is rebuilt with the new
            // brush rather than recoloured in place.
            b.MouseEnter += delegate
            {
                b.Content = Icons.Build(IconNameFor(glyph), 11, Brushes.White);
            };
            b.MouseLeave += delegate
            {
                b.Content = Icons.Build(IconNameFor(glyph), 11, new SolidColorBrush(CMuted));
            };

            return b;
        }

        private void UpdateNav()
        {
            foreach (var pair in navButtons)
            {
                bool active = pair.Key == activePage;
                pair.Value.Background = active ? new SolidColorBrush(CSurface2) : Brushes.Transparent;
                Border accent;
                if (navAccents.TryGetValue(pair.Key, out accent)) accent.Visibility = active ? Visibility.Visible : Visibility.Collapsed;
                var grid = pair.Value.Content as Grid;
                if (grid == null) continue;
                foreach (UIElement child in grid.Children)
                {
                    var stack = child as StackPanel;
                    if (stack == null) continue;
                    foreach (UIElement inner in stack.Children)
                    {
                        var text = inner as TextBlock;
                        if (text != null) text.Foreground = new SolidColorBrush(active ? CText : CMuted);
                    }
                }
            }
        }

        private void UpdateLanguageUi()
        {
            string[] pages = { "home", "library", "discover", "displays", "performance" };
            foreach (string page in pages)
            {
                TextBlock label;
                if (navLabels.TryGetValue(page, out label)) label.Text = Tr("nav." + page);
            }
        }

        private void SwitchPage(string page)
        {
            activePage = page;
            UpdateNav();
            if (page == "home") pageHost.Content = BuildHome();
            else if (page == "library") pageHost.Content = BuildLibrary();
            else if (page == "discover") pageHost.Content = BuildDiscover();
            else if (page == "displays") pageHost.Content = BuildDisplays();
            else pageHost.Content = BuildPerformance();
            UpdateStatusBar();
        }

        private void UpdateStatusBar()
        {
            if (statusWallpaperText != null)
            {
                string current = config.MonitorVideos.Values.FirstOrDefault(File.Exists);
                statusWallpaperText.Text = current == null ? Tr("display.unset") : Path.GetFileNameWithoutExtension(current);
            }
            if (statusTelemetryText != null)
                statusTelemetryText.Text = Forms.Screen.AllScreens.Length + " " + Tr("apply.screens") + "   ·   " + config.TargetFps + " FPS   ·   " + Tr(config.Mute ? "status.audio.off" : "status.audio.on");
        }

        // ================= DASHBOARD =================

        private UIElement BuildHome()
        {
            var content = PageCanvas();
            content.Children.Add(PageHeading(Tr("home.title"), Tr("home.sub"), null));

            string featurePath = selectedVideo != null && File.Exists(selectedVideo) ? selectedVideo : config.Library.FirstOrDefault(File.Exists);
            content.Children.Add(BuildHero(featurePath));

            var stats = new System.Windows.Controls.Primitives.UniformGrid { Columns = 4, Margin = new Thickness(0, 18, 0, 6) };
            stats.Children.Add(MetricTile(Forms.Screen.AllScreens.Length.ToString(), Tr("metric.monitor"), Icons.Displays, CAccent));
            stats.Children.Add(MetricTile(config.MonitorVideos.Count(x => File.Exists(x.Value)).ToString(), Tr("metric.active"), Icons.Apply, CPrimaryHi));
            stats.Children.Add(MetricTile(config.Library.Count(File.Exists).ToString(), Tr("metric.library"), Icons.Library, CAccent));
            stats.Children.Add(MetricTile(catalogItems.Count.ToString(), Tr("metric.catalog"), Icons.Catalog, CPrimaryHi));
            content.Children.Add(stats);

            var recent = config.Library.Where(File.Exists).Reverse().Take(4).ToList();
            content.Children.Add(SectionHeader(Tr("recent"), Tr("view.all"), delegate { SwitchPage("library"); }));
            if (recent.Count == 0)
            {
                content.Children.Add(EmptyCard(Tr("empty.library"), Tr("empty.library.sub")));
            }
            else
            {
                var row = new System.Windows.Controls.Primitives.UniformGrid { Columns = Math.Max(1, recent.Count), Margin = new Thickness(0, 4, 0, 0) };
                foreach (string path in recent) row.Children.Add(SmallWallpaperCard(path));
                content.Children.Add(row);
            }

            var picks = catalogItems.Where(x => !string.Equals(x.Category, "Mature 18+", StringComparison.OrdinalIgnoreCase)).Take(4).ToList();
            if (picks.Count > 0)
            {
                content.Children.Add(SectionHeader(Tr("picks"), Tr("view.all"), delegate { SwitchPage("discover"); }));
                var pickRow = new System.Windows.Controls.Primitives.UniformGrid { Columns = Math.Max(1, picks.Count), Margin = new Thickness(0, 4, 0, 0) };
                foreach (CatalogItem item in picks) pickRow.Children.Add(SmallCatalogCard(item));
                content.Children.Add(pickRow);
            }
            return PageScroll(content);
        }

        private UIElement BuildHero(string path)
        {
            var hero = new Border
            {
                Height = 288,
                Margin = new Thickness(0, 20, 0, 0),
                CornerRadius = new CornerRadius(12),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                ClipToBounds = true
            };
            var grid = new Grid();
            if (path != null && File.Exists(path))
            {
                var image = new Image { Stretch = Stretch.UniformToFill, Opacity = .82 };
                SetVideoThumbnail(path, image);
                grid.Children.Add(image);
            }
            var shade = new Border
            {
                Background = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0),
                    EndPoint = new Point(1, 0),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromArgb(246, 8, 9, 13), 0),
                        new GradientStop(Color.FromArgb(214, 8, 9, 13), .46),
                        new GradientStop(Color.FromArgb(90, 8, 9, 13), .78),
                        new GradientStop(Color.FromArgb(38, 8, 9, 13), 1)
                    }
                }
            };
            grid.Children.Add(shade);

            var copy = new StackPanel { VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(34, 0, 34, 0), MaxWidth = 680, HorizontalAlignment = HorizontalAlignment.Left };
            var eyebrow = new StackPanel { Orientation = Orientation.Horizontal };
            eyebrow.Children.Add(new Border { Width = 22, Height = 3, CornerRadius = new CornerRadius(2), Background = new SolidColorBrush(CPrimary), VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 10, 0) });
            eyebrow.Children.Add(new TextBlock { Text = Tr("hero.featured"), Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 10.5, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center });
            copy.Children.Add(eyebrow);
            string title = path != null ? Path.GetFileNameWithoutExtension(path) : Tr("home.hero");
            copy.Children.Add(new TextBlock
            {
                Text = title,
                Foreground = Brushes.White,
                FontFamily = FDisplay,
                FontSize = 33,
                FontWeight = FontWeights.SemiBold,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 10, 0, 0)
            });
            string meta = path != null
                ? (IsImageFile(path) ? "STATIC IMAGE" : "VIDEO LOOP") + "     /     " + FormatBytes(new FileInfo(path).Length) + "     /     " + config.TargetFps + " FPS"
                : Tr("home.hero.sub");
            copy.Children.Add(new TextBlock { Text = meta, Foreground = new SolidColorBrush(CMuted), FontSize = 11, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 8, 0, 0) });
            var actions = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 20, 0, 0) };
            var apply = PrimaryButton(Icons.Apply, Tr("action.apply"));
            apply.Height = 42;
            if (path != null) apply.Click += delegate { ShowApplyDialog(path); };
            actions.Children.Add(apply);
            var details = GhostButton(Tr("action.details"));
            details.Height = 42;
            details.Margin = new Thickness(10, 0, 0, 0);
            if (path != null) details.Click += delegate { ShowVideoDetails(path); };
            actions.Children.Add(details);
            var browse = GhostButton(Tr("action.catalog"));
            browse.Height = 42;
            browse.Margin = new Thickness(10, 0, 0, 0);
            browse.Click += delegate { SwitchPage("discover"); };
            actions.Children.Add(browse);
            copy.Children.Add(actions);
            grid.Children.Add(copy);
            hero.Child = grid;
            return hero;
        }

        private Border MetricTile(string value, string label, string iconName, Color accent)
        {
            var b = new Border
            {
                Margin = new Thickness(0, 0, 12, 0),
                Padding = new Thickness(16, 14, 16, 14),
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1)
            };
            var row = new StackPanel { Orientation = Orientation.Horizontal };
            var iconHost = new Border
            {
                Width = 38,
                Height = 38,
                CornerRadius = new CornerRadius(8),
                Background = new SolidColorBrush(Color.FromArgb(34, accent.R, accent.G, accent.B)),
                VerticalAlignment = VerticalAlignment.Center
            };
            iconHost.Child = Icons.Build(iconName, 16, new SolidColorBrush(accent));
            row.Children.Add(iconHost);
            var stack = new StackPanel { Margin = new Thickness(13, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
            stack.Children.Add(new TextBlock { Text = value, Foreground = new SolidColorBrush(CText), FontFamily = FMono, FontSize = 22, FontWeight = FontWeights.Bold });
            stack.Children.Add(new TextBlock { Text = label, Foreground = new SolidColorBrush(CMuted), FontSize = 10, Margin = new Thickness(0, 2, 0, 0) });
            row.Children.Add(stack);
            b.Child = row;
            return b;
        }

        // ================= LIBRARY =================

        private UIElement BuildLibrary()
        {
            var content = PageCanvas();
            var add = PrimaryButton(Icons.Add, Tr("action.add"));
            add.Click += AddLocalVideo;
            content.Children.Add(PageHeading(Tr("library.title"), config.Library.Count(File.Exists) + " " + Tr("library.items"), add));

            if (!string.IsNullOrWhiteSpace(selectedVideo) && File.Exists(selectedVideo)) content.Children.Add(BuildLibrarySpotlight(selectedVideo));

            var grid = new WrapPanel { Margin = new Thickness(0, 18, 0, 0) };
            foreach (string path in config.Library.Where(File.Exists)) grid.Children.Add(WallpaperCard(path));
            if (grid.Children.Count == 0) grid.Children.Add(EmptyCard(Tr("empty.library"), Tr("empty.library.sub")));
            content.Children.Add(grid);
            return PageScroll(content);
        }

        private UIElement BuildLibrarySpotlight(string path)
        {
            var hero = new Border
            {
                Height = 212,
                Margin = new Thickness(0, 20, 0, 0),
                CornerRadius = new CornerRadius(12),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CPrimary),
                BorderThickness = new Thickness(1),
                ClipToBounds = true
            };
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(340) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var preview = new Grid { Background = new SolidColorBrush(Color.FromRgb(12, 14, 18)) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            SetVideoThumbnail(path, image);
            preview.Children.Add(image);
            var live = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(236, 10, 12, 16)),
                BorderBrush = new SolidColorBrush(CPrimary),
                BorderThickness = new Thickness(0, 0, 0, 2),
                Padding = new Thickness(10, 5, 10, 5),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(14)
            };
            live.Child = new TextBlock { Text = Tr("library.selected"), Foreground = new SolidColorBrush(CText), FontSize = 10, FontWeight = FontWeights.SemiBold };
            preview.Children.Add(live);
            grid.Children.Add(preview);

            var detail = new Grid { Margin = new Thickness(26, 22, 24, 21) };
            detail.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            detail.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock { Text = Tr("library.ready"), Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 10, FontWeight = FontWeights.Bold });
            copy.Children.Add(new TextBlock { Text = Path.GetFileNameWithoutExtension(path), Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 23, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis, Margin = new Thickness(0, 6, 0, 0) });
            string type = IsImageFile(path) ? "STATIC IMAGE" : "VIDEO LOOP";
            copy.Children.Add(new TextBlock { Text = type + "     /     " + FormatBytes(new FileInfo(path).Length) + "     /     TARGET " + config.TargetFps + " FPS", Foreground = new SolidColorBrush(CMuted), FontSize = 10, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 8, 0, 0) });
            detail.Children.Add(copy);
            var actions = new StackPanel { Orientation = Orientation.Horizontal };
            var apply = PrimaryButton("\uE768", Tr("action.apply"));
            apply.Click += delegate { ShowApplyDialog(path); };
            actions.Children.Add(apply);
            var optimize = GhostButton(Tr("action.optimize") + " · " + config.TargetFps + " FPS");
            optimize.Margin = new Thickness(9, 0, 0, 0);
            string optimizePath = path;
            optimize.Click += delegate { selectedVideo = optimizePath; OptimizeSelected(null, null); };
            actions.Children.Add(optimize);
            Grid.SetRow(actions, 1);
            detail.Children.Add(actions);
            Grid.SetColumn(detail, 1);
            grid.Children.Add(detail);
            hero.Child = grid;
            return hero;
        }

        private Border WallpaperCard(string path)
        {
            bool selected = selectedVideo == path;
            var card = new Border
            {
                Width = 268,
                Height = 214,
                Margin = new Thickness(0, 0, 14, 14),
                CornerRadius = new CornerRadius(10),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(selected ? CPrimary : CBorder),
                BorderThickness = new Thickness(selected ? 2 : 1),
                ClipToBounds = true,
                Cursor = Cursors.Hand
            };
            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(150) });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            var media = new Grid { Background = new SolidColorBrush(Color.FromRgb(11, 13, 17)) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            SetVideoThumbnail(path, image, 640);
            media.Children.Add(image);

            var overlay = new Border
            {
                Background = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 1),
                    EndPoint = new Point(0, 0),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromArgb(235, 6, 7, 10), 0),
                        new GradientStop(Color.FromArgb(120, 6, 7, 10), .55),
                        new GradientStop(Color.FromArgb(0, 6, 7, 10), 1)
                    }
                },
                Visibility = Visibility.Collapsed
            };
            var overlayStack = new StackPanel { VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(12) };
            var overlayActions = new StackPanel { Orientation = Orientation.Horizontal };
            string cardPath = path;
            var quickApply = CompactActionButton(Tr("action.apply"));
            quickApply.Click += delegate { ShowApplyDialog(cardPath); };
            overlayActions.Children.Add(quickApply);
            var quickOptimize = CompactActionButton(Tr("action.optimize"));
            quickOptimize.Margin = new Thickness(6, 0, 0, 0);
            quickOptimize.Click += delegate { selectedVideo = cardPath; OptimizeSelected(null, null); };
            overlayActions.Children.Add(quickOptimize);
            overlayStack.Children.Add(overlayActions);
            overlay.Child = overlayStack;
            media.Children.Add(overlay);

            bool isImage = IsImageFile(path);
            var badge = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(236, 10, 12, 16)),
                BorderBrush = new SolidColorBrush(isImage ? CAccent : CPrimary),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(8, 4, 8, 4),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(11)
            };
            badge.Child = new TextBlock { Text = isImage ? "STATIC" : "LOOP", Foreground = new SolidColorBrush(isImage ? CAccent : CPrimaryHi), FontSize = 9, FontWeight = FontWeights.Bold };
            media.Children.Add(badge);
            grid.Children.Add(media);

            var caption = new Grid { Margin = new Thickness(13, 9, 11, 9) };
            caption.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            caption.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var copy = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            copy.Children.Add(new TextBlock { Text = Path.GetFileNameWithoutExtension(path), Foreground = new SolidColorBrush(CText), FontSize = 12.5, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
            copy.Children.Add(new TextBlock { Text = FormatBytes(new FileInfo(path).Length), Foreground = new SolidColorBrush(CMuted), FontSize = 10, Margin = new Thickness(0, 3, 0, 0) });
            caption.Children.Add(copy);
            var more = CompactActionButton(Tr("action.apply"));
            more.Click += delegate { ShowApplyDialog(cardPath); };
            Grid.SetColumn(more, 1);
            caption.Children.Add(more);
            Grid.SetRow(caption, 1);
            grid.Children.Add(caption);
            card.Child = grid;

            card.MouseLeftButtonUp += delegate(object sender, MouseButtonEventArgs e) { if (!ComesFromButton(e.OriginalSource, card)) SelectVideo(cardPath); };
            card.MouseEnter += delegate
            {
                card.BorderBrush = new SolidColorBrush(CPrimary);
                overlay.Visibility = Visibility.Visible;
            };
            card.MouseLeave += delegate
            {
                card.BorderBrush = new SolidColorBrush(selectedVideo == cardPath ? CPrimary : CBorder);
                overlay.Visibility = Visibility.Collapsed;
            };
            return card;
        }

        private Border SmallWallpaperCard(string path)
        {
            var card = new Border
            {
                Height = 128,
                Margin = new Thickness(0, 0, 12, 0),
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                ClipToBounds = true,
                Cursor = Cursors.Hand
            };
            var grid = new Grid();
            var image = new Image { Stretch = Stretch.UniformToFill, Opacity = .92 };
            SetVideoThumbnail(path, image, 640);
            grid.Children.Add(image);
            grid.Children.Add(BottomShade());
            var caption = new StackPanel { VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(11, 0, 11, 9) };
            caption.Children.Add(new TextBlock { Text = Path.GetFileNameWithoutExtension(path), Foreground = Brushes.White, FontSize = 11.5, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
            caption.Children.Add(new TextBlock { Text = FormatBytes(new FileInfo(path).Length), Foreground = new SolidColorBrush(CMuted), FontSize = 9.5, Margin = new Thickness(0, 2, 0, 0) });
            grid.Children.Add(caption);
            card.Child = grid;
            string cardPath = path;
            card.MouseEnter += delegate { card.BorderBrush = new SolidColorBrush(CPrimary); };
            card.MouseLeave += delegate { card.BorderBrush = new SolidColorBrush(CBorder); };
            card.MouseLeftButtonUp += delegate { SelectVideo(cardPath); ShowApplyDialog(cardPath); };
            return card;
        }

        private Border SmallCatalogCard(CatalogItem item)
        {
            var card = new Border
            {
                Height = 128,
                Margin = new Thickness(0, 0, 12, 0),
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                ClipToBounds = true,
                Cursor = Cursors.Hand
            };
            var grid = new Grid();
            var image = new Image { Stretch = Stretch.UniformToFill, Opacity = .92 };
            SetCatalogThumbnail(item.ThumbnailUrl, image, 640);
            grid.Children.Add(image);
            grid.Children.Add(BottomShade());
            var caption = new StackPanel { VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(11, 0, 11, 9) };
            caption.Children.Add(new TextBlock { Text = item.Title ?? "Untitled", Foreground = Brushes.White, FontSize = 11.5, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
            caption.Children.Add(new TextBlock { Text = CategoryLabel(item.Category ?? "Collection"), Foreground = new SolidColorBrush(CMuted), FontSize = 9.5, Margin = new Thickness(0, 2, 0, 0), TextTrimming = TextTrimming.CharacterEllipsis });
            grid.Children.Add(caption);
            card.Child = grid;
            CatalogItem cardItem = item;
            card.MouseEnter += delegate { card.BorderBrush = new SolidColorBrush(CPrimary); };
            card.MouseLeave += delegate { card.BorderBrush = new SolidColorBrush(CBorder); };
            card.MouseLeftButtonUp += delegate { SelectCatalogItem(cardItem); SwitchPage("discover"); };
            return card;
        }

        private static Border BottomShade()
        {
            // Taller and stronger than a token fade: titles sit over bright,
            // busy wallpaper thumbnails, and a weak scrim made them unreadable.
            return new Border
            {
                Background = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 1),
                    EndPoint = new Point(0, 0),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromArgb(252, 5, 6, 9), 0),
                        new GradientStop(Color.FromArgb(215, 5, 6, 9), .45),
                        new GradientStop(Color.FromArgb(90, 5, 6, 9), .78),
                        new GradientStop(Color.FromArgb(0, 5, 6, 9), 1)
                    }
                }
            };
        }

        // ================= DISCOVER =================

        private UIElement BuildDiscover()
        {
            catalogCardViews.Clear();
            double layoutWidth = ActualWidth > 0 ? ActualWidth : Width;
            bool compactWindow = layoutWidth < 1240;
            bool narrowWindow = layoutWidth < 1060;
            catalogLayoutBucket = narrowWindow ? 0 : compactWindow ? 1 : 2;
            int dynamicCount = catalogItems.Count(x => string.Equals(x.Kind, "dynamic", StringComparison.OrdinalIgnoreCase));

            var root = new Grid { Background = new SolidColorBrush(CWindow) };
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(74) });
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

            var header = new Grid { Margin = new Thickness(26, 14, 24, 10) };
            header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var title = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            title.Children.Add(new TextBlock { Text = Tr("catalog.title"), Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 26, FontWeight = FontWeights.SemiBold });
            string subtitle = catalogItems.Count + " wallpaper   ·   " + dynamicCount + " loop   ·   " + (catalogSearch == "" ? Tr("catalog.browse") : "\"" + catalogSearch + "\"");
            title.Children.Add(new TextBlock { Text = subtitle, Foreground = new SolidColorBrush(CMuted), FontSize = 10.5, Margin = new Thickness(0, 4, 0, 0) });
            header.Children.Add(title);
            var refresh = GhostButton(Tr("action.reload"));
            refresh.Height = 36;
            refresh.VerticalAlignment = VerticalAlignment.Center;
            refresh.Click += RefreshCatalog;
            Grid.SetColumn(refresh, 1);
            header.Children.Add(refresh);
            root.Children.Add(header);

            var workspace = new Grid { Margin = new Thickness(24, 0, 24, 18) };
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(narrowWindow ? 0 : compactWindow ? 316 : 366) });

            var browser = new Grid { Margin = new Thickness(0, 0, narrowWindow ? 0 : 16, 0) };
            browser.RowDefinitions.Add(new RowDefinition { Height = new GridLength(46) });
            browser.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            var categoryItems = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Top };
            string[] preferred = { "Semua", "Anime Loop", "Anime Girls", "Anime-style", "Dynamic", "Mature 18+", "Nature", "Space", "Architecture", "City", "Abstract" };
            foreach (string category in preferred.Where(x => x == "Semua" || catalogItems.Any(i => string.Equals(i.Category, x, StringComparison.OrdinalIgnoreCase))))
            {
                string categoryValue = category;
                int count = category == "Semua" ? catalogItems.Count : catalogItems.Count(x => string.Equals(x.Category, category, StringComparison.OrdinalIgnoreCase));
                bool active = category == activeCategory;
                var chipText = new StackPanel { Orientation = Orientation.Horizontal };
                chipText.Children.Add(new TextBlock { Text = CategoryLabel(category), Foreground = new SolidColorBrush(active ? Colors.White : CMuted), FontSize = 11.5, FontWeight = active ? FontWeights.SemiBold : FontWeights.Normal, VerticalAlignment = VerticalAlignment.Center });
                chipText.Children.Add(new TextBlock { Text = count.ToString(), Foreground = new SolidColorBrush(active ? Colors.White : CDim), FontSize = 9.5, Margin = new Thickness(8, 1, 0, 0), VerticalAlignment = VerticalAlignment.Center });
                var chip = new Button
                {
                    Content = chipText,
                    Height = 34,
                    Margin = new Thickness(0, 0, 8, 0),
                    Padding = new Thickness(14, 0, 14, 0),
                    BorderThickness = new Thickness(1),
                    BorderBrush = new SolidColorBrush(active ? CPrimary : CBorder),
                    Background = new SolidColorBrush(active ? CPrimary : CSurface),
                    Cursor = Cursors.Hand
                };
                System.Windows.Automation.AutomationProperties.SetName(chip, CategoryLabel(category) + " " + count);
                bool chipActive = active;
                chip.MouseEnter += delegate { if (!chipActive) { chip.Background = new SolidColorBrush(CSurfaceHover); chip.BorderBrush = new SolidColorBrush(CBorderHot); } };
                chip.MouseLeave += delegate { if (!chipActive) { chip.Background = new SolidColorBrush(CSurface); chip.BorderBrush = new SolidColorBrush(CBorder); } };
                chip.Click += delegate
                {
                    if (categoryValue == "Mature 18+" && !config.ShowMature) { if (!ShowMatureGate()) return; config.ShowMature = true; store.Save(config); }
                    activeCategory = categoryValue;
                    catalogVisibleCount = 30;
                    selectedCatalogItem = null;
                    SwitchPage("discover");
                };
                SetRoundedButton(chip, 17);
                categoryItems.Children.Add(chip);
            }
            var categoryScroll = new ScrollViewer { Content = categoryItems, HorizontalScrollBarVisibility = ScrollBarVisibility.Hidden, VerticalScrollBarVisibility = ScrollBarVisibility.Disabled, PanningMode = PanningMode.HorizontalOnly };
            browser.Children.Add(categoryScroll);

            IEnumerable<CatalogItem> visible = activeCategory == "Semua" ? catalogItems : catalogItems.Where(x => string.Equals(x.Category, activeCategory, StringComparison.OrdinalIgnoreCase));
            if (!config.ShowMature)
                visible = visible.Where(x => !string.Equals(x.Category, "Mature 18+", StringComparison.OrdinalIgnoreCase));
            if (!string.IsNullOrWhiteSpace(catalogSearch)) visible = visible.Where(x => (x.Title ?? "").IndexOf(catalogSearch, StringComparison.OrdinalIgnoreCase) >= 0 || (x.Author ?? "").IndexOf(catalogSearch, StringComparison.OrdinalIgnoreCase) >= 0 || (x.Category ?? "").IndexOf(catalogSearch, StringComparison.OrdinalIgnoreCase) >= 0);
            var visibleList = visible.ToList();
            if (selectedCatalogItem == null || !visibleList.Contains(selectedCatalogItem)) selectedCatalogItem = visibleList.FirstOrDefault();
            var galleryContent = new StackPanel { Margin = new Thickness(0, 0, 2, 0) };
            var galleryScroll = new ScrollViewer { Content = galleryContent, VerticalScrollBarVisibility = ScrollBarVisibility.Hidden, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, PanningMode = PanningMode.VerticalOnly };
            catalogGalleryScroll = galleryScroll;
            PopulateCatalogGallery(galleryContent, galleryScroll, visibleList, false);
            Grid.SetRow(galleryScroll, 1);
            browser.Children.Add(galleryScroll);
            workspace.Children.Add(browser);

            catalogInspectorHost = new ContentControl { Content = BuildCatalogInspector(selectedCatalogItem) };
            catalogInspectorHost.Visibility = narrowWindow ? Visibility.Collapsed : Visibility.Visible;
            Grid.SetColumn(catalogInspectorHost, 1);
            workspace.Children.Add(catalogInspectorHost);
            Grid.SetRow(workspace, 1);
            root.Children.Add(workspace);
            return root;
        }

        private void OnWindowSizeChanged(object sender, SizeChangedEventArgs e)
        {
            if (!IsLoaded || activePage != "discover") return;
            int nextBucket = ActualWidth < 1060 ? 0 : ActualWidth < 1240 ? 1 : 2;
            if (nextBucket == catalogLayoutBucket) return;
            double offset = catalogGalleryScroll == null ? 0 : catalogGalleryScroll.VerticalOffset;
            catalogLayoutBucket = nextBucket;
            Dispatcher.BeginInvoke(new Action(delegate
            {
                SwitchPage("discover");
                if (catalogGalleryScroll != null) catalogGalleryScroll.ScrollToVerticalOffset(offset);
            }), DispatcherPriority.Loaded);
        }

        private void PopulateCatalogGallery(StackPanel content, ScrollViewer scroll, List<CatalogItem> items, bool preserveOffset)
        {
            double offset = preserveOffset ? scroll.VerticalOffset : 0;
            content.Children.Clear();
            content.Children.Add(BuildCatalogGrid(items.Take(catalogVisibleCount).ToList()));
            if (items.Count > catalogVisibleCount)
            {
                var more = GhostButton(Tr("action.more") + "   ·   " + Math.Min(catalogVisibleCount, items.Count) + " / " + items.Count);
                more.Margin = new Thickness(0, 16, 12, 14);
                more.HorizontalAlignment = HorizontalAlignment.Center;
                more.Click += delegate
                {
                    catalogVisibleCount += 30;
                    PopulateCatalogGallery(content, scroll, items, true);
                };
                content.Children.Add(more);
            }
            if (preserveOffset)
                Dispatcher.BeginInvoke(new Action(delegate { scroll.ScrollToVerticalOffset(offset); }), DispatcherPriority.Loaded);
        }

        private UIElement BuildCatalogGrid(List<CatalogItem> items)
        {
            if (items.Count == 0) return EmptyCard(Tr("empty.catalog"), Tr("empty.catalog.sub"));
            int columns = catalogLayoutBucket == 2 ? 3 : 2;
            var gallery = new System.Windows.Controls.Primitives.UniformGrid { Columns = columns };
            foreach (CatalogItem item in items) gallery.Children.Add(CatalogTile(item));
            return gallery;
        }

        private Border CatalogTile(CatalogItem item)
        {
            bool selected = object.ReferenceEquals(selectedCatalogItem, item);
            var card = new Border
            {
                Margin = new Thickness(0, 0, 12, 12),
                CornerRadius = new CornerRadius(10),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(selected ? CPrimary : CBorder),
                BorderThickness = new Thickness(selected ? 2 : 1),
                ClipToBounds = true,
                Cursor = Cursors.Hand,
                MinHeight = 208
            };
            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(62) });
            var media = new Grid { Background = new SolidColorBrush(Color.FromRgb(11, 13, 17)) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            SetCatalogThumbnail(item.ThumbnailUrl, image, 640);
            media.Children.Add(image);

            var hoverShade = new Border
            {
                Background = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 1),
                    EndPoint = new Point(0, 0),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromArgb(238, 6, 7, 10), 0),
                        new GradientStop(Color.FromArgb(140, 6, 7, 10), .5),
                        new GradientStop(Color.FromArgb(0, 6, 7, 10), 1)
                    }
                },
                Visibility = Visibility.Collapsed
            };
            CatalogItem cardItem = item;
            var hoverStack = new StackPanel { VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(12) };
            hoverStack.Children.Add(new TextBlock { Text = item.Title ?? "Untitled", Foreground = Brushes.White, FontSize = 12.5, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
            hoverStack.Children.Add(new TextBlock { Text = (item.Author ?? "Unknown") + "   ·   " + CategoryLabel(item.Category ?? "Collection"), Foreground = new SolidColorBrush(CMuted), FontSize = 10, Margin = new Thickness(0, 3, 0, 8), TextTrimming = TextTrimming.CharacterEllipsis });
            var hoverActions = new StackPanel { Orientation = Orientation.Horizontal };
            var primary = CompactActionButton(GetLocalCatalogPath(item) != null ? Tr("action.apply") : Tr("action.download"));
            primary.Click += async delegate { await ActivateCatalogItem(cardItem); };
            hoverActions.Children.Add(primary);
            var details = CompactActionButton(Tr("action.details"));
            details.Margin = new Thickness(6, 0, 0, 0);
            details.Click += delegate { ShowCatalogDetails(cardItem); };
            hoverActions.Children.Add(details);
            hoverStack.Children.Add(hoverActions);
            hoverShade.Child = hoverStack;
            media.Children.Add(hoverShade);

            bool isDynamic = string.Equals(item.Kind, "dynamic", StringComparison.OrdinalIgnoreCase);
            var kindBadge = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(236, 10, 12, 16)),
                BorderBrush = new SolidColorBrush(isDynamic ? CPrimary : CAccent),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(8, 4, 8, 4),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(11)
            };
            kindBadge.Child = new TextBlock { Text = isDynamic ? "LOOP" : "STATIC", Foreground = new SolidColorBrush(isDynamic ? CPrimaryHi : CAccent), FontSize = 9, FontWeight = FontWeights.Bold };
            media.Children.Add(kindBadge);
            grid.Children.Add(media);

            var caption = new Grid { Margin = new Thickness(12, 8, 10, 8) };
            caption.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            caption.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var copy = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            copy.Children.Add(new TextBlock { Text = item.Title ?? "Untitled", Foreground = new SolidColorBrush(CText), FontSize = 12, FontWeight = FontWeights.SemiBold, TextTrimming = TextTrimming.CharacterEllipsis });
            copy.Children.Add(new TextBlock { Text = CategoryLabel(item.Category ?? "Collection"), Foreground = new SolidColorBrush(CMuted), FontSize = 9.5, Margin = new Thickness(0, 3, 0, 0), TextTrimming = TextTrimming.CharacterEllipsis });
            caption.Children.Add(copy);
            var download = CompactActionButton(GetLocalCatalogPath(item) != null ? Tr("action.apply") : Tr("action.download"));
            download.Click += async delegate { await ActivateCatalogItem(cardItem); };
            Grid.SetColumn(download, 1);
            caption.Children.Add(download);
            Grid.SetRow(caption, 1);
            grid.Children.Add(caption);
            card.Child = grid;
            catalogCardViews[item] = card;
            card.MouseLeftButtonUp += delegate(object sender, MouseButtonEventArgs e) { if (!ComesFromButton(e.OriginalSource, card)) SelectCatalogItem(cardItem); };
            card.MouseEnter += delegate
            {
                card.BorderBrush = new SolidColorBrush(CPrimary);
                hoverShade.Visibility = Visibility.Visible;
            };
            card.MouseLeave += delegate
            {
                card.BorderBrush = new SolidColorBrush(object.ReferenceEquals(selectedCatalogItem, cardItem) ? CPrimary : CBorder);
                hoverShade.Visibility = Visibility.Collapsed;
            };
            return card;
        }

        private UIElement BuildCatalogInspector(CatalogItem item)
        {
            var panel = new Border
            {
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(11),
                ClipToBounds = true
            };
            if (item == null)
            {
                panel.Child = new TextBlock { Text = Tr("empty.catalog"), Foreground = new SolidColorBrush(CMuted), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
                return panel;
            }
            var content = new Grid();
            content.RowDefinitions.Add(new RowDefinition { Height = new GridLength(44) });
            content.RowDefinitions.Add(new RowDefinition { Height = new GridLength(Height < 720 ? 168 : 208) });
            content.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            var inspectorHeader = new Grid { Background = new SolidColorBrush(Color.FromRgb(14, 17, 23)) };
            inspectorHeader.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(42) });
            inspectorHeader.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var headerGlyph = Icons.Build(Icons.Library, 13, new SolidColorBrush(CPrimaryHi));
            headerGlyph.HorizontalAlignment = HorizontalAlignment.Center;
            inspectorHeader.Children.Add(headerGlyph);
            var inspectorTitle = new TextBlock { Text = Tr("library.selected"), Foreground = new SolidColorBrush(CText), FontSize = 12, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(inspectorTitle, 1);
            inspectorHeader.Children.Add(inspectorTitle);
            content.Children.Add(inspectorHeader);
            var preview = new Grid { Background = new SolidColorBrush(Color.FromRgb(11, 13, 17)) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            SetCatalogThumbnail(item.ThumbnailUrl, image);
            preview.Children.Add(image);
            var type = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(236, 10, 12, 16)),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(9, 5, 9, 5),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Bottom,
                Margin = new Thickness(14)
            };
            type.Child = new TextBlock { Text = string.Equals(item.Kind, "dynamic", StringComparison.OrdinalIgnoreCase) ? "VIDEO LOOP" : "IMAGE", Foreground = new SolidColorBrush(CText), FontSize = 9, FontWeight = FontWeights.Bold };
            preview.Children.Add(type);
            Grid.SetRow(preview, 1);
            content.Children.Add(preview);
            var detail = new Grid { Margin = new Thickness(20, 18, 20, 18) };
            detail.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            detail.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock { Text = item.Title ?? "Untitled", Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 20, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
            copy.Children.Add(new TextBlock { Text = CategoryLabel(item.Category ?? "Collection"), Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 11, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 7, 0, 18) });
            copy.Children.Add(InspectorRow("CREATOR", item.Author ?? "Unknown"));
            copy.Children.Add(InspectorRow("LICENSE", item.License ?? "Check source"));
            copy.Children.Add(InspectorRow("TYPE", string.Equals(item.Kind, "dynamic", StringComparison.OrdinalIgnoreCase) ? "Dynamic loop" : "Static image"));
            copy.Children.Add(BuildInspectorOutputSummary());
            var copyScroll = new ScrollViewer { Content = copy, VerticalScrollBarVisibility = ScrollBarVisibility.Hidden, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, PanningMode = PanningMode.VerticalOnly };
            detail.Children.Add(copyScroll);
            var actions = new StackPanel();
            CatalogItem cardItem = item;
            bool isLocal = GetLocalCatalogPath(item) != null;
            var download = PrimaryButton(isLocal ? Icons.Apply : Icons.Download, isLocal ? Tr("action.apply") : Tr("catalog.download"));
            download.HorizontalAlignment = HorizontalAlignment.Stretch;
            download.Click += async delegate { await ActivateCatalogItem(cardItem); };
            actions.Children.Add(download);
            var details = GhostButton(Tr("action.details"));
            details.Margin = new Thickness(0, 8, 0, 0);
            details.HorizontalAlignment = HorizontalAlignment.Stretch;
            details.Click += delegate { ShowCatalogDetails(cardItem); };
            actions.Children.Add(details);
            if (!string.IsNullOrWhiteSpace(item.SourceUrl) && Uri.IsWellFormedUriString(item.SourceUrl, UriKind.Absolute))
            {
                string sourceUrl = item.SourceUrl;
                var source = GhostButton(Tr("catalog.source"));
                source.Margin = new Thickness(0, 8, 0, 0);
                source.HorizontalAlignment = HorizontalAlignment.Stretch;
                source.Click += delegate { Process.Start(new ProcessStartInfo(sourceUrl) { UseShellExecute = true }); };
                actions.Children.Add(source);
            }
            Grid.SetRow(actions, 1);
            detail.Children.Add(actions);
            Grid.SetRow(detail, 2);
            content.Children.Add(detail);
            panel.Child = content;
            return panel;
        }

        private UIElement InspectorRow(string label, string value)
        {
            var row = new StackPanel { Margin = new Thickness(0, 0, 0, 13) };
            row.Children.Add(new TextBlock { Text = label, Foreground = new SolidColorBrush(CDim), FontSize = 9, FontWeight = FontWeights.SemiBold });
            row.Children.Add(new TextBlock { Text = value, Foreground = new SolidColorBrush(CText), FontSize = 12, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 3, 0, 0) });
            return row;
        }

        private UIElement BuildInspectorOutputSummary()
        {
            Forms.Screen[] screens = OrderedScreens();
            var section = new StackPanel { Margin = new Thickness(0, 5, 0, 18) };
            var heading = new Grid { Margin = new Thickness(0, 0, 0, 9) };
            heading.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            heading.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            heading.Children.Add(new TextBlock { Text = Tr("inspector.output"), Foreground = new SolidColorBrush(CText), FontSize = 11, FontWeight = FontWeights.SemiBold });
            var count = new TextBlock { Text = screens.Length + " " + Tr("inspector.detected"), Foreground = new SolidColorBrush(CMuted), FontSize = 9, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(count, 1);
            heading.Children.Add(count);
            section.Children.Add(heading);

            var monitorGrid = new System.Windows.Controls.Primitives.UniformGrid { Columns = Math.Max(1, Math.Min(3, screens.Length)), Margin = new Thickness(0, 0, 0, 10) };
            for (int index = 0; index < screens.Length; index++)
            {
                Forms.Screen screen = screens[index];
                var monitor = new Border
                {
                    Height = 52,
                    Margin = new Thickness(0, 0, index == screens.Length - 1 ? 0 : 6, 0),
                    Background = new SolidColorBrush(CSurface2),
                    BorderBrush = new SolidColorBrush(screen.Primary ? CPrimary : CBorder),
                    BorderThickness = new Thickness(1),
                    CornerRadius = new CornerRadius(6)
                };
                var monitorCopy = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
                monitorCopy.Children.Add(new TextBlock { Text = (index + 1).ToString(), Foreground = new SolidColorBrush(CText), FontFamily = FMono, FontSize = 15, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center });
                monitorCopy.Children.Add(new TextBlock { Text = screen.Bounds.Width + "×" + screen.Bounds.Height, Foreground = new SolidColorBrush(CMuted), FontFamily = FMono, FontSize = 8, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 3, 0, 0) });
                monitor.Child = monitorCopy;
                monitorGrid.Children.Add(monitor);
            }
            section.Children.Add(monitorGrid);
            section.Children.Add(new TextBlock { Text = config.TargetFps + " FPS   ·   " + Tr(config.Mute ? "status.audio.off" : "status.audio.on"), Foreground = new SolidColorBrush(CMuted), FontSize = 10 });
            return section;
        }

        // ================= DISPLAYS =================

        private UIElement BuildDisplays()
        {
            var content = PageCanvas();
            content.Children.Add(PageHeading(Tr("display.title"), Tr("display.sub"), null));

            var profiles = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 20, 0, 6) };
            profiles.Children.Add(new TextBlock { Text = Tr("profile.title"), Foreground = new SolidColorBrush(CMuted), FontSize = 12, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 12, 0) });
            var saveProfile = GhostButton(Tr("profile.save"));
            saveProfile.Height = 34;
            saveProfile.Margin = new Thickness(0, 0, 8, 0);
            saveProfile.Click += delegate { SaveDisplayProfile(); };
            profiles.Children.Add(saveProfile);
            foreach (string profileName in config.DisplayProfiles.Keys.OrderBy(x => x))
            {
                string name = profileName;
                var profile = GhostButton(name);
                profile.Height = 34;
                profile.Margin = new Thickness(0, 0, 8, 0);
                profile.Click += delegate { LoadDisplayProfile(name); };
                profiles.Children.Add(profile);
            }
            content.Children.Add(profiles);

            var list = new WrapPanel { Margin = new Thickness(0, 12, 0, 0) };
            int index = 1;
            foreach (Forms.Screen screen in Forms.Screen.AllScreens)
            {
                string current;
                config.MonitorVideos.TryGetValue(screen.DeviceName, out current);
                list.Children.Add(MonitorCard(screen, index, current));
                index++;
            }
            content.Children.Add(list);
            return PageScroll(content);
        }

        private Border MonitorCard(Forms.Screen screen, int index, string current)
        {
            bool hasWallpaper = File.Exists(current);
            var card = new Border
            {
                Width = 306,
                Height = 262,
                Margin = new Thickness(0, 0, 16, 16),
                CornerRadius = new CornerRadius(11),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(screen.Primary ? CPrimary : CBorder),
                BorderThickness = new Thickness(1),
                ClipToBounds = true
            };
            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(150) });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            var media = new Grid { Background = new SolidColorBrush(Color.FromRgb(11, 13, 17)) };
            if (hasWallpaper)
            {
                var image = new Image { Stretch = Stretch.UniformToFill };
                SetVideoThumbnail(current, image, 640);
                media.Children.Add(image);
                media.Children.Add(BottomShade());
            }
            else
            {
                var empty = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
                empty.Children.Add(Icons.Build(Icons.Displays, 24, new SolidColorBrush(CDim)));
                empty.Children.Add(new TextBlock { Text = Tr("display.unset"), Foreground = new SolidColorBrush(CMuted), FontSize = 11, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 8, 0, 0) });
                media.Children.Add(empty);
            }
            var number = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(240, 10, 12, 16)),
                BorderBrush = new SolidColorBrush(screen.Primary ? CPrimary : CBorderHot),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(6),
                Padding = new Thickness(10, 5, 10, 5),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(12)
            };
            var numberStack = new StackPanel { Orientation = Orientation.Horizontal };
            numberStack.Children.Add(new TextBlock { Text = "MONITOR " + index, Foreground = new SolidColorBrush(CText), FontFamily = FMono, FontSize = 9.5, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center });
            if (screen.Primary)
                numberStack.Children.Add(new TextBlock { Text = "· " + Tr("display.primary").ToUpperInvariant(), Foreground = new SolidColorBrush(CPrimaryHi), FontFamily = FMono, FontSize = 9.5, FontWeight = FontWeights.Bold, Margin = new Thickness(6, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center });
            number.Child = numberStack;
            media.Children.Add(number);

            var resolution = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(220, 10, 12, 16)),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(8, 4, 8, 4),
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(12)
            };
            resolution.Child = new TextBlock { Text = screen.Bounds.Width + " × " + screen.Bounds.Height, Foreground = new SolidColorBrush(CAccent), FontFamily = FMono, FontSize = 9.5, FontWeight = FontWeights.Bold };
            media.Children.Add(resolution);
            grid.Children.Add(media);

            var body = new Grid { Margin = new Thickness(14, 11, 12, 12) };
            body.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock
            {
                Text = hasWallpaper ? Path.GetFileNameWithoutExtension(current) : Tr("display.unset"),
                Foreground = new SolidColorBrush(hasWallpaper ? CText : CMuted),
                FontSize = 12.5,
                FontWeight = FontWeights.SemiBold,
                TextTrimming = TextTrimming.CharacterEllipsis
            });
            copy.Children.Add(new TextBlock
            {
                Text = screen.DeviceName + (hasWallpaper ? "   ·   " + (IsImageFile(current) ? "STATIC" : "LOOP") : ""),
                Foreground = new SolidColorBrush(CDim),
                FontSize = 9.5,
                Margin = new Thickness(0, 3, 0, 0),
                TextTrimming = TextTrimming.CharacterEllipsis
            });
            body.Children.Add(copy);
            var actions = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 8, 0, 0) };
            var apply = CompactActionButton(Tr("action.apply"));
            string device = screen.DeviceName;
            apply.Click += delegate { ApplyToMonitor(device); };
            actions.Children.Add(apply);
            var stop = CompactActionButton(Tr("action.stop"));
            stop.Margin = new Thickness(6, 0, 0, 0);
            stop.Click += delegate { StopMonitor(device); };
            actions.Children.Add(stop);
            Grid.SetRow(actions, 1);
            body.Children.Add(actions);
            Grid.SetRow(body, 1);
            grid.Children.Add(body);
            card.Child = grid;
            return card;
        }

        // ================= PERFORMANCE =================

        private UIElement BuildPerformance()
        {
            var content = PageCanvas();
            content.Children.Add(PageHeading(Tr("perf.title"), Tr("perf.sub"), null));

            var topRow = new Grid { Margin = new Thickness(0, 20, 0, 0) };
            topRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.25, GridUnitType.Star) });
            topRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            topRow.Children.Add(SettingGroup(Tr("fps.title"), Tr("fps.sub"), BuildFpsPicker()));
            var telemetryCard = BuildTelemetryCard();
            Grid.SetColumn(telemetryCard, 1);
            topRow.Children.Add(telemetryCard);
            content.Children.Add(topRow);

            content.Children.Add(SettingGroup(Tr("auto.title"), Tr("auto.sub"), BuildToggleStack()));
            var note = new Border
            {
                Margin = new Thickness(0, 16, 0, 0),
                Padding = new Thickness(18),
                CornerRadius = new CornerRadius(9),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                Background = new SolidColorBrush(CSurface)
            };
            var noteStack = new StackPanel { Orientation = Orientation.Horizontal };
            var noteIcon = new Border { Width = 34, Height = 34, CornerRadius = new CornerRadius(8), Background = new SolidColorBrush(CAccentSoft), VerticalAlignment = VerticalAlignment.Top };
            noteIcon.Child = Icons.Build(Icons.Performance, 15, new SolidColorBrush(CAccent));
            noteStack.Children.Add(noteIcon);
            noteStack.Children.Add(new TextBlock { Text = Tr("perf.note"), Foreground = new SolidColorBrush(CMuted), TextWrapping = TextWrapping.Wrap, FontSize = 12, Margin = new Thickness(14, 0, 0, 0), MaxWidth = 760, VerticalAlignment = VerticalAlignment.Center });
            note.Child = noteStack;
            content.Children.Add(note);
            return PageScroll(content);
        }

        private Border BuildTelemetryCard()
        {
            var card = new Border
            {
                // Sits in a grid column beside the FPS picker, so it needs a left
                // gutter rather than the top margin it used to carry (that pushed
                // it down out of alignment with its neighbour). The bottom margin
                // is kept so it still clears the section below when the columns
                // stack on a narrow window.
                Margin = new Thickness(16, 0, 0, 22),
                Padding = new Thickness(20, 18, 20, 18),
                CornerRadius = new CornerRadius(9),
                Background = new SolidColorBrush(CSurface),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                MinWidth = 320
            };
            var stack = new StackPanel();
            stack.Children.Add(new TextBlock { Text = Tr("perf.live"), Foreground = new SolidColorBrush(CText), FontSize = 14, FontWeight = FontWeights.SemiBold });
            stack.Children.Add(new TextBlock { Text = Tr("perf.live.sub"), Foreground = new SolidColorBrush(CMuted), FontSize = 11, Margin = new Thickness(0, 5, 0, 14), TextWrapping = TextWrapping.Wrap });
            var grid = new Grid();
            // Two columns, not three: "Wallpaper aktif" is a long label and at a
            // third of this card's width it clipped to a bare "M" against the
            // card edge. Two columns give each value room for the number plus its
            // unit, and the third metric moves to its own row.
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            telemetryCpu = TelemetryCell(grid, 0, 0, Tr("stat.cpu"), CAccent, Icons.Cpu);
            telemetryRam = TelemetryCell(grid, 1, 0, Tr("stat.ram"), CPrimaryHi, Icons.Memory);
            telemetryActive = TelemetryCell(grid, 0, 1, Tr("stat.active"), CWarning, Icons.Apply);
            stack.Children.Add(grid);
            card.Child = stack;
            UpdateTelemetry();
            return card;
        }

        private TextBlock TelemetryCell(Grid grid, int column, int row, string label, Color accent, string iconName)
        {
            // Each cell is a 3-row block (head, value, spacer) inside its grid row
            // so cells in the same row line up regardless of label wrapping.
            if (grid.RowDefinitions.Count <= row)
                grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            var cell = new StackPanel
            {
                Margin = new Thickness(column == 0 ? 0 : 12, row == 0 ? 0 : 16, 0, 0)
            };
            var head = new StackPanel { Orientation = Orientation.Horizontal };
            head.Children.Add(Icons.Build(iconName, 11, new SolidColorBrush(accent)));
            head.Children.Add(new TextBlock
            {
                Text = label.ToUpperInvariant(),
                Foreground = new SolidColorBrush(CDim),
                FontSize = 9,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(6, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center,
                // Let a long label wrap instead of being clipped mid-word.
                TextWrapping = TextWrapping.Wrap
            });
            cell.Children.Add(head);
            var value = new TextBlock
            {
                Text = "…",
                Foreground = new SolidColorBrush(CText),
                FontFamily = FMono,
                FontSize = 19,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 6, 0, 0),
                // The number itself must never clip; if it ever does not fit, an
                // ellipsis is still far better than a truncated digit.
                TextTrimming = TextTrimming.CharacterEllipsis
            };
            cell.Children.Add(value);
            Grid.SetColumn(cell, column);
            Grid.SetRow(cell, row);
            grid.Children.Add(cell);
            return value;
        }

        private void UpdateTelemetry()
        {
            try
            {
                Process process = Process.GetCurrentProcess();
                process.Refresh();
                if (telemetryRam != null) telemetryRam.Text = (process.WorkingSet64 / (1024d * 1024d)).ToString("0") + " MB";
                if (telemetryActive != null) telemetryActive.Text = config.MonitorVideos.Count(x => File.Exists(x.Value)).ToString();
                if (telemetryCpu != null)
                {
                    DateTime now = DateTime.Now;
                    TimeSpan cpu = process.TotalProcessorTime;
                    if (lastCpuStamp != DateTime.MinValue)
                    {
                        double seconds = Math.Max(0.001, (now - lastCpuStamp).TotalSeconds);
                        double usage = (cpu - lastCpuTime).TotalSeconds / (seconds * Math.Max(1, Environment.ProcessorCount)) * 100d;
                        telemetryCpu.Text = usage.ToString("0.0") + " %";
                    }
                    else
                    {
                        // First sample: fall back to the process lifetime average so
                        // the card never shows an empty placeholder while it waits
                        // for the next health tick.
                        double uptime = Math.Max(0.001, (now - process.StartTime).TotalSeconds);
                        double lifetime = cpu.TotalSeconds / (uptime * Math.Max(1, Environment.ProcessorCount)) * 100d;
                        telemetryCpu.Text = lifetime.ToString("0.0") + " %";
                    }
                    lastCpuStamp = now;
                    lastCpuTime = cpu;
                }
            }
            catch { }
        }

        private UIElement BuildFpsPicker()
        {
            var stack = new StackPanel { Orientation = Orientation.Horizontal };
            foreach (int fps in new[] { 15, 24, 30 })
            {
                bool active = fps == config.TargetFps;
                var content = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
                content.Children.Add(new TextBlock { Text = fps.ToString(), Foreground = new SolidColorBrush(active ? Colors.White : CText), FontFamily = FMono, FontSize = 18, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center });
                content.Children.Add(new TextBlock { Text = "FPS", Foreground = new SolidColorBrush(active ? Colors.White : CMuted), FontSize = 8.5, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 1, 0, 0) });
                var b = new Button
                {
                    Content = content,
                    Tag = fps,
                    Width = 78,
                    Height = 58,
                    Margin = new Thickness(0, 0, 8, 0),
                    Cursor = Cursors.Hand,
                    BorderThickness = new Thickness(1),
                    BorderBrush = new SolidColorBrush(active ? CPrimary : CBorder),
                    Background = new SolidColorBrush(active ? CPrimary : CSurface2)
                };
                System.Windows.Automation.AutomationProperties.SetName(b, fps + " FPS");
                b.MouseEnter += delegate { if ((int)b.Tag != config.TargetFps) { b.Background = new SolidColorBrush(CSurfaceHover); b.BorderBrush = new SolidColorBrush(CBorderHot); } };
                b.MouseLeave += delegate { if ((int)b.Tag != config.TargetFps) { b.Background = new SolidColorBrush(CSurface2); b.BorderBrush = new SolidColorBrush(CBorder); } };
                b.Click += delegate(object sender, RoutedEventArgs e)
                {
                    config.TargetFps = (int)((Button)sender).Tag;
                    manager.SetTargetFps(config.TargetFps);
                    store.Save(config);
                    SwitchPage("performance");
                    ShowToast(Tr("toast.fps") + ": " + config.TargetFps);
                };
                SetRoundedButton(b, 9);
                stack.Children.Add(b);
            }
            return stack;
        }

        private UIElement BuildToggleStack()
        {
            var stack = new StackPanel();
            stack.Children.Add(SettingCheck(Tr("check.fullscreen"), config.PauseFullscreen, delegate(bool v) { config.PauseFullscreen = v; }));
            stack.Children.Add(SettingCheck(Tr("check.maximized"), config.PauseMaximized, delegate(bool v) { config.PauseMaximized = v; }));
            stack.Children.Add(SettingCheck(Tr("check.battery"), config.PauseOnBattery, delegate(bool v) { config.PauseOnBattery = v; }));
            stack.Children.Add(SettingCheck(Tr("check.mute"), config.Mute, delegate(bool v) { config.Mute = v; manager.SetMute(v); }));
            stack.Children.Add(SettingCheck(Tr("check.startup"), config.StartWithWindows, delegate(bool v) { config.StartWithWindows = v; SetStartup(v); }));
            return stack;
        }

        private Button SettingCheck(string text, bool value, Action<bool> changed)
        {
            bool enabled = value;
            var row = new Grid { Width = 320 };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var label = new TextBlock { Text = text, Foreground = new SolidColorBrush(CText), FontSize = 12, VerticalAlignment = VerticalAlignment.Center };
            row.Children.Add(label);
            var track = new Border
            {
                Width = 44,
                Height = 22,
                CornerRadius = new CornerRadius(11),
                Background = new SolidColorBrush(enabled ? CPrimary : CSurfaceHover),
                BorderBrush = new SolidColorBrush(enabled ? CPrimary : CBorder),
                BorderThickness = new Thickness(1),
                Padding = new Thickness(3)
            };
            var knob = new Border { Width = 14, Height = 14, CornerRadius = new CornerRadius(7), Background = new SolidColorBrush(CText), HorizontalAlignment = enabled ? HorizontalAlignment.Right : HorizontalAlignment.Left };
            track.Child = knob;
            Grid.SetColumn(track, 1);
            row.Children.Add(track);
            var button = new Button { Content = row, Height = 38, Margin = new Thickness(0, 2, 0, 2), Padding = new Thickness(0), Background = Brushes.Transparent, BorderThickness = new Thickness(0), Cursor = Cursors.Hand, HorizontalContentAlignment = HorizontalAlignment.Stretch };
            // Without its own template this button inherits the Aero hover, which
            // paints a pale blue rectangle across the whole settings row.
            SetRoundedButton(button, 7);
            System.Windows.Automation.AutomationProperties.SetName(button, text);
            button.Click += delegate
            {
                enabled = !enabled;
                track.Background = new SolidColorBrush(enabled ? CPrimary : CSurfaceHover);
                track.BorderBrush = new SolidColorBrush(enabled ? CPrimary : CBorder);
                knob.HorizontalAlignment = enabled ? HorizontalAlignment.Right : HorizontalAlignment.Left;
                changed(enabled);
                store.Save(config);
                UpdateStatusBar();
            };
            return button;
        }

        // ================= DETAIL DIALOGS =================

        private void ShowVideoDetails(string path)
        {
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path)) { ShowToast(Tr("toast.pick")); return; }
            var dialog = new Window
            {
                Owner = this,
                Title = Path.GetFileNameWithoutExtension(path),
                Width = 880,
                Height = 520,
                MinWidth = 720,
                MinHeight = 440,
                WindowStyle = WindowStyle.None,
                ResizeMode = ResizeMode.CanResize,
                ShowInTaskbar = false,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = new SolidColorBrush(CWindow),
                Foreground = new SolidColorBrush(CText)
            };
            WindowChrome.SetWindowChrome(dialog, new WindowChrome { CaptionHeight = 46, CornerRadius = new CornerRadius(13), ResizeBorderThickness = new Thickness(6), GlassFrameThickness = new Thickness(0), UseAeroCaptionButtons = false });
            var root = new Grid { Margin = new Thickness(20) };
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.6, GridUnitType.Star) });
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var preview = new Border { CornerRadius = new CornerRadius(11), Background = new SolidColorBrush(CSurface), ClipToBounds = true, BorderBrush = new SolidColorBrush(CBorder), BorderThickness = new Thickness(1) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            preview.Child = image;
            SetVideoThumbnail(path, image);
            root.Children.Add(preview);
            var side = new Grid { Margin = new Thickness(24, 6, 6, 6) };
            side.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            side.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock { Text = IsImageFile(path) ? "STATIC IMAGE" : "VIDEO LOOP", Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 10, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 10) });
            copy.Children.Add(new TextBlock { Text = Path.GetFileNameWithoutExtension(path), Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 22, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
            copy.Children.Add(new TextBlock { Text = FormatBytes(new FileInfo(path).Length) + "   ·   " + config.TargetFps + " FPS   ·   " + Tr(config.Mute ? "status.audio.off" : "status.audio.on"), Foreground = new SolidColorBrush(CMuted), FontSize = 12, Margin = new Thickness(0, 10, 0, 20) });
            copy.Children.Add(new TextBlock { Text = path, Foreground = new SolidColorBrush(CDim), FontSize = 10, TextWrapping = TextWrapping.Wrap });
            copy.Children.Add(BuildInspectorOutputSummary());
            var scroll = new ScrollViewer { Content = copy, VerticalScrollBarVisibility = ScrollBarVisibility.Hidden, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, PanningMode = PanningMode.VerticalOnly };
            side.Children.Add(scroll);
            var actions = new StackPanel();
            string detailPath = path;
            var apply = PrimaryButton("\uE768", Tr("action.apply"));
            apply.HorizontalAlignment = HorizontalAlignment.Stretch;
            apply.Click += delegate { dialog.Close(); ShowApplyDialog(detailPath); };
            actions.Children.Add(apply);
            var optimize = GhostButton(Tr("action.optimize") + " · " + config.TargetFps + " FPS");
            optimize.Margin = new Thickness(0, 9, 0, 0);
            optimize.HorizontalAlignment = HorizontalAlignment.Stretch;
            optimize.Click += delegate { dialog.Close(); selectedVideo = detailPath; OptimizeSelected(null, null); };
            actions.Children.Add(optimize);
            var open = GhostButton(config.Language == "id" ? "Buka lokasi file" : "Open file location");
            open.Margin = new Thickness(0, 9, 0, 0);
            open.HorizontalAlignment = HorizontalAlignment.Stretch;
            open.Click += delegate { Process.Start("explorer.exe", "/select,\"" + detailPath + "\""); };
            actions.Children.Add(open);
            var close = GhostButton(Tr("action.cancel"));
            close.Margin = new Thickness(0, 9, 0, 0);
            close.HorizontalAlignment = HorizontalAlignment.Stretch;
            close.Click += delegate { dialog.Close(); };
            actions.Children.Add(close);
            Grid.SetRow(actions, 1);
            side.Children.Add(actions);
            Grid.SetColumn(side, 1);
            root.Children.Add(side);
            dialog.Content = root;
            dialog.ShowDialog();
        }

        private void ShowCatalogDetails(CatalogItem item)
        {
            var dialog = new Window
            {
                Owner = this,
                Title = item.Title ?? Tr("catalog.details"),
                Width = 900,
                Height = 540,
                MinWidth = 760,
                MinHeight = 470,
                WindowStyle = WindowStyle.None,
                ResizeMode = ResizeMode.CanResize,
                ShowInTaskbar = false,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = new SolidColorBrush(CWindow),
                Foreground = new SolidColorBrush(CText)
            };
            WindowChrome.SetWindowChrome(dialog, new WindowChrome { CaptionHeight = 46, CornerRadius = new CornerRadius(13), ResizeBorderThickness = new Thickness(6), GlassFrameThickness = new Thickness(0), UseAeroCaptionButtons = false });
            var root = new Grid { Margin = new Thickness(20) };
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.65, GridUnitType.Star) });
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var preview = new Border { CornerRadius = new CornerRadius(11), Background = new SolidColorBrush(CSurface), ClipToBounds = true, BorderBrush = new SolidColorBrush(CBorder), BorderThickness = new Thickness(1) };
            var image = new Image { Stretch = Stretch.UniformToFill };
            preview.Child = image;
            SetCatalogThumbnail(item.ThumbnailUrl, image);
            root.Children.Add(preview);
            var side = new Grid { Margin = new Thickness(24, 6, 6, 6) };
            side.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            side.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock { Text = string.Equals(item.Kind, "dynamic", StringComparison.OrdinalIgnoreCase) ? "DYNAMIC" : "STATIC", Foreground = new SolidColorBrush(CPrimaryHi), FontSize = 10, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 10) });
            copy.Children.Add(new TextBlock { Text = item.Title ?? Tr("catalog.details"), Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 23, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
            copy.Children.Add(new TextBlock { Text = CategoryLabel(item.Category ?? "Collection"), Foreground = new SolidColorBrush(CMuted), FontSize = 13, Margin = new Thickness(0, 10, 0, 22) });
            copy.Children.Add(InspectorRow("CREATOR", item.Author ?? "Unknown"));
            copy.Children.Add(InspectorRow("LICENSE", item.License ?? "Check source"));
            copy.Children.Add(BuildInspectorOutputSummary());
            side.Children.Add(copy);
            var actions = new StackPanel();
            CatalogItem cardItem = item;
            bool isLocal = GetLocalCatalogPath(item) != null;
            var download = PrimaryButton(isLocal ? "\uE768" : "\uE896", isLocal ? Tr("action.apply") : Tr("catalog.download"));
            download.HorizontalAlignment = HorizontalAlignment.Stretch;
            download.Click += async delegate
            {
                string path = GetLocalCatalogPath(cardItem);
                if (path == null) path = await DownloadItem(cardItem);
                if (path != null) { dialog.Close(); ShowApplyDialog(path); }
            };
            actions.Children.Add(download);
            if (!string.IsNullOrWhiteSpace(item.SourceUrl) && Uri.IsWellFormedUriString(item.SourceUrl, UriKind.Absolute))
            {
                string sourceUrl = item.SourceUrl;
                var source = GhostButton(Tr("catalog.source"));
                source.Margin = new Thickness(0, 9, 0, 0);
                source.HorizontalAlignment = HorizontalAlignment.Stretch;
                source.Click += delegate { Process.Start(new ProcessStartInfo(sourceUrl) { UseShellExecute = true }); };
                actions.Children.Add(source);
            }
            var close = GhostButton(Tr("action.cancel"));
            close.Margin = new Thickness(0, 9, 0, 0);
            close.HorizontalAlignment = HorizontalAlignment.Stretch;
            close.Click += delegate { dialog.Close(); };
            actions.Children.Add(close);
            Grid.SetRow(actions, 1);
            side.Children.Add(actions);
            Grid.SetColumn(side, 1);
            root.Children.Add(side);
            dialog.Content = root;
            dialog.ShowDialog();
        }

        private bool ShowMatureGate()
        {
            var dialog = new Window
            {
                Owner = this,
                Title = Tr("mature.title"),
                Width = 470,
                Height = 260,
                WindowStyle = WindowStyle.None,
                ResizeMode = ResizeMode.NoResize,
                ShowInTaskbar = false,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = new SolidColorBrush(CSurface),
                Foreground = new SolidColorBrush(CText)
            };
            WindowChrome.SetWindowChrome(dialog, new WindowChrome { CaptionHeight = 0, CornerRadius = new CornerRadius(13), ResizeBorderThickness = new Thickness(0), GlassFrameThickness = new Thickness(0) });
            var root = new Grid { Margin = new Thickness(26, 24, 26, 22) };
            root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var heading = new StackPanel { Orientation = Orientation.Horizontal };
            var icon = new Border { Width = 36, Height = 36, CornerRadius = new CornerRadius(18), Background = new SolidColorBrush(Color.FromRgb(66, 49, 30)), Child = Icons.Build(Icons.Warning, 16, new SolidColorBrush(CWarning)) };
            heading.Children.Add(icon);
            heading.Children.Add(new TextBlock { Text = Tr("mature.title"), Foreground = new SolidColorBrush(CText), FontSize = 19, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(12, 0, 0, 0) });
            root.Children.Add(heading);
            var body = new TextBlock { Text = Tr("mature.warning"), Foreground = new SolidColorBrush(CMuted), TextWrapping = TextWrapping.Wrap, FontSize = 13, LineHeight = 21, Margin = new Thickness(0, 20, 0, 16), VerticalAlignment = VerticalAlignment.Center };
            Grid.SetRow(body, 1);
            root.Children.Add(body);
            var actions = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
            var cancel = GhostButton(Tr("action.cancel"));
            cancel.Click += delegate { dialog.DialogResult = false; };
            var confirm = PrimaryButton(Icons.Check, Tr("action.continue"));
            confirm.Margin = new Thickness(10, 0, 0, 0);
            confirm.Click += delegate { dialog.DialogResult = true; };
            actions.Children.Add(cancel);
            actions.Children.Add(confirm);
            Grid.SetRow(actions, 2);
            root.Children.Add(actions);
            dialog.Content = root;
            return dialog.ShowDialog() == true;
        }

        private string PromptProfileName()
        {
            string result = null;
            var dialog = new Window
            {
                Owner = this,
                Title = Tr("profile.save"),
                Width = 400,
                Height = 200,
                WindowStyle = WindowStyle.None,
                ResizeMode = ResizeMode.NoResize,
                ShowInTaskbar = false,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = new SolidColorBrush(CSurface)
            };
            WindowChrome.SetWindowChrome(dialog, new WindowChrome { CaptionHeight = 36, CornerRadius = new CornerRadius(12), ResizeBorderThickness = new Thickness(0), GlassFrameThickness = new Thickness(0) });
            var panel = new StackPanel { Margin = new Thickness(24, 22, 24, 20) };
            panel.Children.Add(new TextBlock { Text = Tr("profile.name"), Foreground = new SolidColorBrush(CText), FontSize = 16, FontWeight = FontWeights.SemiBold });
            var input = new TextBox { Text = "Setup " + (config.DisplayProfiles.Count + 1), Height = 36, Margin = new Thickness(0, 14, 0, 16), Padding = new Thickness(10, 7, 10, 6), Foreground = new SolidColorBrush(CText), Background = new SolidColorBrush(CSurface2), BorderBrush = new SolidColorBrush(CBorder) };
            panel.Children.Add(input);
            var actions = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
            var cancel = GhostButton(Tr("action.cancel"));
            cancel.Click += delegate { dialog.DialogResult = false; };
            var save = PrimaryButton(Icons.Save, Tr("profile.save"));
            save.Margin = new Thickness(8, 0, 0, 0);
            save.Click += delegate { result = input.Text.Trim(); if (!string.IsNullOrWhiteSpace(result)) dialog.DialogResult = true; };
            actions.Children.Add(cancel);
            actions.Children.Add(save);
            panel.Children.Add(actions);
            dialog.Content = panel;
            return dialog.ShowDialog() == true ? result : null;
        }

        private void SaveDisplayProfile()
        {
            string name = PromptProfileName();
            if (string.IsNullOrWhiteSpace(name)) return;
            config.DisplayProfiles[name] = new Dictionary<string, string>(config.MonitorVideos, StringComparer.OrdinalIgnoreCase);
            store.Save(config);
            ShowToast(name + " · " + Tr("profile.save"));
            SwitchPage("displays");
        }

        private void LoadDisplayProfile(string name)
        {
            Dictionary<string, string> profile;
            if (!config.DisplayProfiles.TryGetValue(name, out profile)) return;
            manager.CloseAll();
            config.MonitorVideos.Clear();
            foreach (Forms.Screen screen in Forms.Screen.AllScreens)
            {
                string path;
                if (!profile.TryGetValue(screen.DeviceName, out path) || !File.Exists(path)) continue;
                config.MonitorVideos[screen.DeviceName] = path;
                manager.Apply(screen, path, config.Mute, config.TargetFps);
            }
            store.Save(config);
            ShowToast(name + " · " + Tr("profile.title"));
            SwitchPage("displays");
        }

        private void ShowApplyDialog(string path)
        {
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path)) { ShowToast(Tr("toast.pick")); return; }
            selectedVideo = path;
            Forms.Screen[] screens = OrderedScreens();
            var dialog = new Window
            {
                Owner = this,
                Title = Tr("action.apply"),
                Width = Math.Max(580, Math.Min(980, 240 + screens.Length * 195)),
                Height = 420,
                WindowStyle = WindowStyle.None,
                ResizeMode = ResizeMode.NoResize,
                ShowInTaskbar = false,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = new SolidColorBrush(CWindow),
                Foreground = new SolidColorBrush(CText)
            };
            WindowChrome.SetWindowChrome(dialog, new WindowChrome { CaptionHeight = 0, CornerRadius = new CornerRadius(12), ResizeBorderThickness = new Thickness(0), GlassFrameThickness = new Thickness(0) });
            var root = new Grid { Margin = new Thickness(26, 24, 26, 22) };
            root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var heading = new Grid();
            heading.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            heading.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var headingCopy = new StackPanel();
            headingCopy.Children.Add(new TextBlock { Text = Tr("apply.choose"), Foreground = new SolidColorBrush(CText), FontSize = 21, FontWeight = FontWeights.SemiBold });
            headingCopy.Children.Add(new TextBlock { Text = Path.GetFileNameWithoutExtension(path), Foreground = new SolidColorBrush(CMuted), FontSize = 12, Margin = new Thickness(0, 5, 0, 0), TextTrimming = TextTrimming.CharacterEllipsis });
            heading.Children.Add(headingCopy);
            var close = IconButton("\uE8BB", Tr("action.cancel"));
            close.Click += delegate { dialog.Close(); };
            Grid.SetColumn(close, 1);
            heading.Children.Add(close);
            root.Children.Add(heading);

            var choices = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
            for (int index = 0; index < screens.Length; index++)
            {
                Forms.Screen screen = screens[index];
                int displayNumber = index + 1;
                var monitor = MonitorChoice("Monitor " + displayNumber, screen.Bounds.Width + " × " + screen.Bounds.Height, screen.Primary ? Tr("display.primary") : "", false);
                Forms.Screen targetScreen = screen;
                monitor.Click += delegate { ApplyPathToScreens(path, new[] { targetScreen }); dialog.Close(); };
                choices.Children.Add(monitor);
            }
            var all = MonitorChoice(Tr("apply.all"), screens.Length + " " + Tr("apply.screens"), Tr("apply.together"), true);
            all.Click += delegate { ApplyPathToScreens(path, screens); dialog.Close(); };
            choices.Children.Add(all);
            var choiceScroller = new ScrollViewer { Content = choices, HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, VerticalScrollBarVisibility = ScrollBarVisibility.Disabled, Margin = new Thickness(0, 20, 0, 10), PanningMode = PanningMode.HorizontalOnly };
            Grid.SetRow(choiceScroller, 1);
            root.Children.Add(choiceScroller);

            var hint = new TextBlock { Text = Tr("apply.hint"), Foreground = new SolidColorBrush(CDim), FontSize = 11, HorizontalAlignment = HorizontalAlignment.Center };
            Grid.SetRow(hint, 2);
            root.Children.Add(hint);
            dialog.Content = root;
            dialog.ShowDialog();
        }

        private Button MonitorChoice(string title, string resolution, string note, bool emphasized)
        {
            var content = new StackPanel { Margin = new Thickness(14, 16, 14, 15) };
            var display = new Border
            {
                Width = 78,
                Height = 48,
                CornerRadius = new CornerRadius(6),
                BorderBrush = new SolidColorBrush(emphasized ? CPrimaryHi : CPrimary),
                BorderThickness = new Thickness(2),
                Background = new SolidColorBrush(emphasized ? CPrimarySoft : CSurface2),
                HorizontalAlignment = HorizontalAlignment.Center
            };
            display.Child = Icons.Build(emphasized ? Icons.AllDisplays : Icons.Displays, 20, new SolidColorBrush(emphasized ? CPrimaryHi : CPrimary));
            content.Children.Add(display);
            content.Children.Add(new TextBlock { Text = title, Foreground = new SolidColorBrush(CText), FontSize = 13, FontWeight = FontWeights.SemiBold, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 12, 0, 0) });
            content.Children.Add(new TextBlock { Text = resolution, Foreground = new SolidColorBrush(CMuted), FontSize = 10, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 4, 0, 0) });
            if (!string.IsNullOrWhiteSpace(note)) content.Children.Add(new TextBlock { Text = note, Foreground = new SolidColorBrush(emphasized ? CPrimaryHi : CPrimary), FontSize = 10, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 3, 0, 0) });
            var button = new Button
            {
                Content = content,
                Width = 172,
                Height = 182,
                Margin = new Thickness(6),
                Background = new SolidColorBrush(emphasized ? CPrimary : CSurface),
                BorderBrush = new SolidColorBrush(emphasized ? CPrimary : CBorder),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand,
                HorizontalContentAlignment = HorizontalAlignment.Stretch,
                VerticalContentAlignment = VerticalAlignment.Stretch
            };
            System.Windows.Automation.AutomationProperties.SetName(button, title);
            button.MouseEnter += delegate { button.BorderBrush = new SolidColorBrush(CPrimaryHi); button.Background = new SolidColorBrush(emphasized ? CPrimaryHi : CSurfaceHover); };
            button.MouseLeave += delegate { button.BorderBrush = new SolidColorBrush(emphasized ? CPrimary : CBorder); button.Background = new SolidColorBrush(emphasized ? CPrimary : CSurface); };
            SetRoundedButton(button, 10);
            return button;
        }

        // ================= ACTIONS =================

        private void SelectCatalogItem(CatalogItem item)
        {
            selectedCatalogItem = item;
            if (catalogInspectorHost != null) catalogInspectorHost.Content = BuildCatalogInspector(item);
            foreach (var pair in catalogCardViews)
            {
                pair.Value.BorderBrush = new SolidColorBrush(object.ReferenceEquals(pair.Key, item) ? CPrimary : CBorder);
                pair.Value.BorderThickness = new Thickness(object.ReferenceEquals(pair.Key, item) ? 2 : 1);
            }
        }

        private void SelectVideo(string path)
        {
            selectedVideo = path;
            ShowToast(Tr("toast.selected") + ": " + Path.GetFileNameWithoutExtension(path));
            if (activePage == "library") SwitchPage("library");
            UpdateStatusBar();
        }

        private void ApplyToMonitor(string device)
        {
            if (string.IsNullOrEmpty(selectedVideo) || !File.Exists(selectedVideo)) { ShowToast(Tr("toast.pick")); return; }
            Forms.Screen screen = Forms.Screen.AllScreens.FirstOrDefault(x => x.DeviceName == device);
            if (screen == null) { ShowToast(Tr("toast.monitor")); return; }
            manager.Apply(screen, selectedVideo, config.Mute, config.TargetFps);
            config.MonitorVideos[device] = selectedVideo;
            store.Save(config);
            ShowToast(Tr("toast.applied"));
            SwitchPage("displays");
        }

        private void ApplyPathToScreens(string path, IEnumerable<Forms.Screen> screens)
        {
            selectedVideo = path;
            foreach (Forms.Screen screen in screens)
            {
                manager.Apply(screen, path, config.Mute, config.TargetFps);
                config.MonitorVideos[screen.DeviceName] = path;
            }
            store.Save(config);
            ShowToast(Tr("toast.applied"));
            UpdateStatusBar();
        }

        private void StopMonitor(string device)
        {
            manager.Remove(device);
            config.MonitorVideos.Remove(device);
            store.Save(config);
            ShowToast(Tr("toast.stopped"));
            SwitchPage("displays");
        }

        private void AddLocalVideo(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog { Title = Tr("action.add"), Filter = "Wallpaper|*.mp4;*.m4v;*.wmv;*.avi;*.mov;*.webm;*.jpg;*.jpeg;*.png;*.bmp|Video|*.mp4;*.m4v;*.wmv;*.avi;*.mov;*.webm|Gambar|*.jpg;*.jpeg;*.png;*.bmp|Semua file|*.*", Multiselect = true };
            if (dialog.ShowDialog(this) != true) return;
            foreach (string file in dialog.FileNames)
                if (!config.Library.Contains(file, StringComparer.OrdinalIgnoreCase)) config.Library.Add(file);
            store.Save(config);
            selectedVideo = dialog.FileNames.Last();
            ShowToast(dialog.FileNames.Length + " · " + Tr("library.title"));
            SwitchPage("library");
            ShowApplyDialog(selectedVideo);
        }

        private async void OptimizeSelected(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(selectedVideo) || !File.Exists(selectedVideo)) { ShowToast(Tr("toast.video")); return; }
            string selectedExt = Path.GetExtension(selectedVideo).ToLowerInvariant();
            if (selectedExt == ".jpg" || selectedExt == ".jpeg" || selectedExt == ".png" || selectedExt == ".bmp") { ShowToast(Tr("toast.static")); return; }
            string ffmpeg = FindFfmpeg();
            if (ffmpeg == null) { ShowToast(Tr("toast.ffmpeg")); return; }
            Directory.CreateDirectory(store.Downloads);
            string output = Path.Combine(store.Downloads, Path.GetFileNameWithoutExtension(selectedVideo) + "_" + config.TargetFps + "fps.mp4");
            ShowToast(Tr("toast.optimizing") + " · " + config.TargetFps + " FPS");
            string input = selectedVideo;
            int fps = config.TargetFps;
            int code = await Task.Run(delegate
            {
                var start = new ProcessStartInfo { FileName = ffmpeg, Arguments = "-y -i \"" + input + "\" -vf fps=" + fps + " -an -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p -movflags +faststart \"" + output + "\"", UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true };
                using (var p = Process.Start(start)) { p.StandardError.ReadToEnd(); p.WaitForExit(); return p.ExitCode; }
            });
            if (code == 0 && File.Exists(output))
            {
                if (!config.Library.Contains(output, StringComparer.OrdinalIgnoreCase)) config.Library.Add(output);
                selectedVideo = output;
                store.Save(config);
                ShowToast(Tr("toast.ready"));
                SwitchPage("library");
            }
            else ShowToast(Tr("toast.failed"));
        }

        private void LoadBundledCatalog()
        {
            try
            {
                string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "catalog.json");
                if (!File.Exists(path)) return;
                catalogItems.Clear();
                catalogItems.AddRange(ReadCatalog(File.ReadAllText(path)));
            }
            catch { }
        }

        private async void RefreshCatalog(object sender, RoutedEventArgs e)
        {
            string url = config.FeedUrl == null ? "" : config.FeedUrl.Trim();
            if (string.IsNullOrEmpty(url)) { LoadBundledCatalog(); SwitchPage("discover"); ShowToast(Tr("toast.catalog")); return; }
            try
            {
                ShowToast(Tr("toast.cataloging"));
                string json;
                using (var client = new WebClient()) { client.Headers.Add("User-Agent", "LumaWall/1.2"); json = await client.DownloadStringTaskAsync(url); }
                catalogItems.Clear();
                catalogItems.AddRange(ReadCatalog(json));
                config.FeedUrl = url;
                store.Save(config);
                SwitchPage("discover");
                ShowToast(Tr("toast.catalog"));
            }
            catch (Exception ex) { ShowToast("Katalog: " + ex.Message); }
        }

        private static List<CatalogItem> ReadCatalog(string json)
        {
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(json))) return (List<CatalogItem>)new DataContractJsonSerializer(typeof(List<CatalogItem>)).ReadObject(stream);
        }

        private string GetLocalCatalogPath(CatalogItem item)
        {
            if (item == null || string.IsNullOrWhiteSpace(item.VideoUrl)) return null;
            Uri remote;
            if (Uri.TryCreate(item.VideoUrl, UriKind.Absolute, out remote) && (remote.Scheme == "http" || remote.Scheme == "https")) return null;
            try
            {
                string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
                string source = Path.GetFullPath(Path.Combine(root, item.VideoUrl));
                return source.StartsWith(root, StringComparison.OrdinalIgnoreCase) && File.Exists(source) ? source : null;
            }
            catch { return null; }
        }

        private async Task ActivateCatalogItem(CatalogItem item)
        {
            string path = GetLocalCatalogPath(item);
            if (path == null) path = await DownloadItem(item);
            if (path != null) ShowApplyDialog(path);
        }

        private async Task<string> DownloadItem(CatalogItem item)
        {
            try
            {
                Directory.CreateDirectory(store.Downloads);
                Uri remote;
                bool isRemote = Uri.TryCreate(item.VideoUrl, UriKind.Absolute, out remote) && (remote.Scheme == "http" || remote.Scheme == "https");
                string sourceExt = Path.GetExtension(isRemote ? remote.AbsolutePath : item.VideoUrl);
                if (string.IsNullOrEmpty(sourceExt) || sourceExt.Length > 5) sourceExt = string.Equals(item.Kind, "dynamic", StringComparison.OrdinalIgnoreCase) ? ".mp4" : ".jpg";
                bool generateLoop = string.Equals(item.Animation, "kenburns", StringComparison.OrdinalIgnoreCase);
                string ext = generateLoop ? ".mp4" : sourceExt;
                string safe = string.Join("_", (item.Title ?? "wallpaper").Split(Path.GetInvalidFileNameChars()));
                string destination = Path.Combine(store.Downloads, safe + ext);
                ShowToast(Tr("toast.downloading") + " " + item.Title + "…");
                string downloadTarget = generateLoop ? destination + ".source" + sourceExt : destination;
                if (isRemote)
                {
                    using (var client = new WebClient())
                    {
                        client.Headers.Add("User-Agent", "LumaWall/1.0");
                        if (Uri.IsWellFormedUriString(item.SourceUrl, UriKind.Absolute)) client.Headers.Add("Referer", item.SourceUrl);
                        string downloadTitle = item.Title;
                        client.DownloadProgressChanged += delegate(object s, DownloadProgressChangedEventArgs e)
                        {
                            Dispatcher.BeginInvoke(new Action(delegate
                            {
                                toastText.Text = Tr("toast.downloading") + " " + downloadTitle + " · " + e.ProgressPercentage + "%";
                                toast.Visibility = Visibility.Visible;
                            }));
                        };
                        await client.DownloadFileTaskAsync(remote, downloadTarget);
                    }
                }
                else
                {
                    string source = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, item.VideoUrl));
                    string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
                    if (!source.StartsWith(root, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Lokasi file tidak diizinkan");
                    File.Copy(source, downloadTarget, true);
                }
                if (generateLoop)
                {
                    bool created = await CreateImageLoop(downloadTarget, destination);
                    try { File.Delete(downloadTarget); } catch { }
                    if (!created) throw new InvalidOperationException("FFmpeg could not create the animated loop.");
                }
                string attribution = "Title: " + (item.Title ?? "Unknown") + Environment.NewLine +
                    "Author: " + (item.Author ?? "Unknown") + Environment.NewLine +
                    "License: " + (item.License ?? "Check source") + Environment.NewLine +
                    "Source: " + (item.SourceUrl ?? "Unknown") + Environment.NewLine;
                File.WriteAllText(destination + ".license.txt", attribution, Encoding.UTF8);
                if (!config.Library.Contains(destination, StringComparer.OrdinalIgnoreCase)) config.Library.Add(destination);
                selectedVideo = destination;
                store.Save(config);
                ShowToast(item.Title + " · " + Tr("library.title"));
                return destination;
            }
            catch (Exception ex) { ShowToast("Download: " + ex.Message); return null; }
        }

        private async Task<bool> CreateImageLoop(string imagePath, string destination)
        {
            string ffmpeg = FindFfmpeg();
            if (ffmpeg == null) return false;
            int code = await Task.Run(delegate
            {
                string filter = "[0:v]split=2[bg][fg];" +
                    "[bg]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,gblur=sigma=35,eq=brightness=-0.18[bg];" +
                    "[fg]scale=1180:680:force_original_aspect_ratio=decrease[fg];" +
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2," +
                    "zoompan=z='1.0+0.015*sin(2*PI*on/192)':x='iw/2-(iw/zoom/2)':" +
                    "y='ih/2-(ih/zoom/2)':d=192:s=1280x720:fps=24[v]";
                var start = new ProcessStartInfo
                {
                    FileName = ffmpeg,
                    Arguments = "-y -i \"" + imagePath + "\" -filter_complex \"" + filter + "\" -map \"[v]\" -frames:v 192 -an -c:v libx264 -preset veryfast -crf 25 -pix_fmt yuv420p -movflags +faststart \"" + destination + "\"",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardError = true
                };
                using (var process = Process.Start(start))
                {
                    process.StandardError.ReadToEnd();
                    process.WaitForExit();
                    return process.ExitCode;
                }
            });
            return code == 0 && File.Exists(destination);
        }

        // ================= THUMBNAILS =================

        private void SetVideoThumbnail(string video, Image target)
        {
            SetVideoThumbnail(video, target, 1280);
        }

        private void SetVideoThumbnail(string video, Image target, int decodeWidth)
        {
            if (string.IsNullOrWhiteSpace(video)) return;
            string ext = Path.GetExtension(video).ToLowerInvariant();
            if (ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".bmp") { SetImage(target, video, decodeWidth); return; }
            string thumb = ThumbnailPath(video);
            // Frames grabbed at low resolution used to be upscaled into the big
            // hero/detail previews and looked blurry. Require a wide capture and
            // regenerate anything smaller, blurry, or a black intro frame.
            bool usable = File.Exists(thumb) && ThumbnailHasContent(thumb);
            if (usable) { SetImage(target, thumb, decodeWidth); return; }
            string ffmpeg = FindFfmpeg();
            if (ffmpeg == null) { if (File.Exists(thumb)) SetImage(target, thumb, decodeWidth); return; }
            string capturePath = thumb;
            string captureVideo = video;
            Task.Run(delegate
            {
                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(capturePath));
                    // Try progressively later timestamps until a frame with real
                    // content comes back (size threshold filters black frames).
                    foreach (int seek in new[] { 1, 3, 5, 8, 0 })
                    {
                        try { if (File.Exists(capturePath)) File.Delete(capturePath); } catch { }
                        var start = new ProcessStartInfo { FileName = ffmpeg, Arguments = "-y -ss " + seek + " -i \"" + captureVideo + "\" -frames:v 1 -vf scale=1280:-2 -q:v 2 \"" + capturePath + "\"", UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true };
                        using (var p = Process.Start(start)) { p.StandardError.ReadToEnd(); p.WaitForExit(); }
                        if (File.Exists(capturePath) && ThumbnailHasContent(capturePath)) break;
                    }
                    if (File.Exists(capturePath)) Dispatcher.BeginInvoke(new Action(delegate { SetImage(target, capturePath, decodeWidth); }));
                }
                catch { }
            });
        }

        /// <summary>
        /// Rejects cached thumbnails that are unusable as a preview: intro
        /// fades decode to a near-black frame, and older caches were captured
        /// at 640px which turns blurry once stretched into the big previews.
        /// </summary>
        private static bool ThumbnailHasContent(string path)
        {
            try
            {
                if (!File.Exists(path)) return false;
                var info = new FileInfo(path);
                if (info.Length < 6000) return false;
                var probe = new BitmapImage();
                probe.BeginInit();
                probe.CacheOption = BitmapCacheOption.OnLoad;
                probe.UriSource = new Uri(path, UriKind.RelativeOrAbsolute);
                probe.EndInit();
                if (probe.PixelWidth < 1000) return false;
                var converted = new FormatConvertedBitmap(probe, PixelFormats.Gray8, null, 0);
                int width = converted.PixelWidth, height = converted.PixelHeight;
                int stride = (width * converted.Format.BitsPerPixel + 7) / 8;
                byte[] pixels = new byte[stride * height];
                converted.CopyPixels(pixels, stride, 0);
                long sum = 0;
                int count = 0;
                for (int y = 0; y < height; y += 4)
                {
                    int row = y * stride;
                    for (int x = 0; x < width; x += 4)
                    {
                        sum += pixels[row + x];
                        count++;
                    }
                }
                if (count == 0) return false;
                // A black intro frame sits around luma 0-3; real artwork is far above.
                return (sum / (double)count) > 8d;
            }
            catch { return false; }
        }

        private string ThumbnailPath(string video)
        {
            byte[] bytes = SHA1.Create().ComputeHash(Encoding.UTF8.GetBytes(video.ToLowerInvariant()));
            string hash = BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant();
            return Path.Combine(store.Folder, "Thumbnails", hash + ".jpg");
        }

        private void SetCatalogThumbnail(string value, Image target)
        {
            SetCatalogThumbnail(value, target, 1280);
        }

        private void SetCatalogThumbnail(string value, Image target, int decodeWidth)
        {
            if (string.IsNullOrEmpty(value)) return;
            if (Uri.IsWellFormedUriString(value, UriKind.Absolute)) SetImage(target, value, decodeWidth);
            else SetImage(target, Path.Combine(AppDomain.CurrentDomain.BaseDirectory, value), decodeWidth);
        }

        private void SetImage(Image image, string path)
        {
            SetImage(image, path, 1280);
        }

        private void SetImage(Image image, string path, int decodeWidth)
        {
            try
            {
                if (path.StartsWith("http://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                {
                    LoadRemoteThumbnail(image, path, decodeWidth);
                    return;
                }
                var bitmap = new BitmapImage();
                bitmap.BeginInit();
                bitmap.CacheOption = BitmapCacheOption.OnLoad;
                // Ignore WPF's URI image cache: thumbnails are regenerated in
                // place when a cached frame was black or low resolution, and the
                // stale decode would otherwise keep showing the old bitmap.
                bitmap.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
                // Decode near source width so full-size previews stay sharp; WPF
                // scales down cheaply for small cards.
                bitmap.DecodePixelWidth = decodeWidth;
                bitmap.UriSource = new Uri(path, UriKind.RelativeOrAbsolute);
                bitmap.EndInit();
                bitmap.Freeze();
                image.Source = bitmap;
            }
            catch { }
        }

        /// <summary>
        /// Loads a remote catalog thumbnail off the UI thread, with a disk cache
        /// and a browser User-Agent.
        ///
        /// Loading these through BitmapImage.UriSource blocked the UI thread for
        /// every visible card (the catalog has thousands of items) and sent no
        /// User-Agent, so hosts that filter unknown clients returned an error and
        /// the card stayed black. Fetching to disk once also means scrolling back
        /// to a card is instant instead of re-downloading.
        /// </summary>
        private void LoadRemoteThumbnail(Image image, string url, int decodeWidth)
        {
            string cached = RemoteThumbnailPath(url);
            if (File.Exists(cached) && new FileInfo(cached).Length > 512)
            {
                ApplyImageFile(image, cached, decodeWidth);
                return;
            }

            Task.Run(delegate
            {
                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(cached));
                    var request = (HttpWebRequest)WebRequest.Create(url);
                    // Some wallpaper hosts reject requests without a browser UA.
                    request.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";
                    request.Accept = "image/avif,image/webp,image/*,*/*;q=0.8";
                    request.Referer = "https://motionbgs.com/";
                    request.Timeout = 20000;
                    request.ReadWriteTimeout = 20000;
                    string temporary = cached + ".part";
                    using (var response = request.GetResponse())
                    using (var source = response.GetResponseStream())
                    using (var target = File.Create(temporary))
                    {
                        source.CopyTo(target);
                    }
                    if (new FileInfo(temporary).Length < 512)
                    {
                        // An error page or an empty body: keep the placeholder
                        // rather than caching something that is not an image.
                        try { File.Delete(temporary); } catch { }
                        return;
                    }
                    if (File.Exists(cached)) File.Delete(cached);
                    File.Move(temporary, cached);
                    image.Dispatcher.BeginInvoke(new Action(delegate
                    {
                        try { ApplyImageFile(image, cached, decodeWidth); } catch { }
                    }));
                }
                catch { }
            });
        }

        private static void ApplyImageFile(Image image, string file, int decodeWidth)
        {
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
            bitmap.DecodePixelWidth = decodeWidth;
            bitmap.UriSource = new Uri(file, UriKind.RelativeOrAbsolute);
            bitmap.EndInit();
            bitmap.Freeze();
            image.Source = bitmap;
        }

        /// <summary>Disk cache location for a remote thumbnail URL.</summary>
        private string RemoteThumbnailPath(string url)
        {
            byte[] hash;
            using (var sha = SHA1.Create())
                hash = sha.ComputeHash(Encoding.UTF8.GetBytes(url));
            var name = new StringBuilder(hash.Length * 2);
            foreach (byte b in hash) name.Append(b.ToString("x2"));
            return Path.Combine(store.Folder, "Thumbnails", name.ToString() + ".jpg");
        }

        // ================= LIFECYCLE =================

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            config.Library = config.Library.Where(File.Exists).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            store.Save(config);
            LoadBundledCatalog();
            selectedVideo = config.Library.FirstOrDefault();
            selectedMonitor = Forms.Screen.PrimaryScreen.DeviceName;
            RestoreWallpapers();
            lastMonitorSignature = GetMonitorSignature();
            healthTimer.Start();
            WarnIfWebView2Missing();
            HandleInvocation(Environment.GetCommandLineArgs().Skip(1).ToArray(), false);
            SwitchPage(Environment.GetCommandLineArgs().Any(x => x == "--library") ? "library" : "discover");
            if (startHidden) Dispatcher.BeginInvoke(new Action(Hide));
        }

        /// <summary>
        /// Tells the user plainly when the WebView2 Runtime is absent.
        ///
        /// Animated wallpapers are rendered by WebView2, so without the Runtime
        /// every video silently fails and the user only sees a black desktop with
        /// no explanation. Windows 11 and updated Windows 10 machines already
        /// include it; this covers the rare machine that does not, where the fix
        /// is a free download the user can act on.
        /// </summary>
        private void WarnIfWebView2Missing()
        {
            try
            {
                string version = CoreWebView2Environment.GetAvailableBrowserVersionString();
                if (string.IsNullOrWhiteSpace(version))
                {
                    AppLog.Write("WebView2 Runtime NOT found; animated wallpapers will not render");
                    Dispatcher.BeginInvoke(new Action(delegate { ShowToast(Tr("toast.noruntime")); }));
                }
                else
                {
                    AppLog.Write("WebView2 Runtime " + version);
                }
            }
            catch (Exception ex)
            {
                AppLog.Write("WebView2 Runtime check failed (treated as missing): " + ex.Message);
                Dispatcher.BeginInvoke(new Action(delegate { ShowToast(Tr("toast.noruntime")); }));
            }
        }

        internal void HandleSecondaryInvocation(string[] args)
        {
            bool backgroundOnly = args.Any(x => string.Equals(x, "--background", StringComparison.OrdinalIgnoreCase)) &&
                !args.Any(x => x.StartsWith("--apply=", StringComparison.OrdinalIgnoreCase));
            bool silent = args.Any(x => string.Equals(x, "--silent", StringComparison.OrdinalIgnoreCase));
            HandleInvocation(args, !backgroundOnly && !silent);
        }

        private void HandleInvocation(string[] args, bool showWindow)
        {
            string applyArgument = args.FirstOrDefault(x => x.StartsWith("--apply=", StringComparison.OrdinalIgnoreCase));
            if (!string.IsNullOrWhiteSpace(applyArgument))
            {
                string requested = applyArgument.Substring("--apply=".Length).Trim().Trim('"');
                if (File.Exists(requested))
                {
                    if (!config.Library.Contains(requested, StringComparer.OrdinalIgnoreCase)) config.Library.Add(requested);
                    selectedVideo = requested;
                    bool allTargets = args.Any(x => string.Equals(x, "--all-monitors", StringComparison.OrdinalIgnoreCase));
                    string monitorArgument = args.FirstOrDefault(x => x.StartsWith("--monitor=", StringComparison.OrdinalIgnoreCase));
                    Forms.Screen[] orderedScreens = OrderedScreens();
                    Forms.Screen[] targets = allTargets ? orderedScreens : new[] { Forms.Screen.PrimaryScreen };
                    int monitorNumber;
                    if (!allTargets && !string.IsNullOrWhiteSpace(monitorArgument) && int.TryParse(monitorArgument.Substring("--monitor=".Length), out monitorNumber) && monitorNumber >= 1 && monitorNumber <= orderedScreens.Length)
                        targets = new[] { orderedScreens[monitorNumber - 1] };
                    foreach (Forms.Screen target in targets)
                    {
                        manager.Apply(target, requested, config.Mute, config.TargetFps);
                        config.MonitorVideos[target.DeviceName] = requested;
                    }
                    store.Save(config);
                    AppLog.Write("Invocation applied wallpaper to " + targets.Length + " monitor(s): " + requested);
                }
            }
            if (showWindow)
            {
                // Page selection from the command line: used by the marketing
                // capture script, and handy for shortcuts that open straight to
                // a section.
                if (args.Any(x => string.Equals(x, "--library", StringComparison.OrdinalIgnoreCase))) SwitchPage("library");
                else if (args.Any(x => string.Equals(x, "--displays", StringComparison.OrdinalIgnoreCase))) SwitchPage("displays");
                else if (args.Any(x => string.Equals(x, "--performance", StringComparison.OrdinalIgnoreCase))) SwitchPage("performance");
                else if (args.Any(x => string.Equals(x, "--discover", StringComparison.OrdinalIgnoreCase))) SwitchPage("discover");
                ShowFromTray();
            }
        }

        private void RestoreWallpapers()
        {
            // Give the manager a way to look up a display's wallpaper. It needs
            // this to rebuild a wallpaper whose window was destroyed along with
            // the desktop (Explorer restart), where the path has to be recovered
            // from the config rather than from the dead window.
            manager.WallpaperLookup = delegate(string device)
            {
                string value;
                return config.MonitorVideos.TryGetValue(device, out value) ? value : null;
            };
            manager.SetDefaults(config.Mute, config.TargetFps);
            foreach (Forms.Screen screen in Forms.Screen.AllScreens)
            {
                string path;
                if (config.MonitorVideos.TryGetValue(screen.DeviceName, out path) && File.Exists(path)) manager.Apply(screen, path, config.Mute, config.TargetFps);
            }
        }

        /// <summary>
        /// Pauses the decoders while the session is locked or the display is
        /// off/asleep. The wallpaper is invisible in those states, so this costs
        /// nothing visually and removes the whole decode load. Called from the
        /// window message hook on the UI thread.
        /// </summary>
        private void SetSystemIdle(bool value)
        {
            if (systemIdle == value) return;
            systemIdle = value;
            ApplyPauseState();
            AppLog.Write("System " + (value ? "locked/display off" : "unlocked/display on") + ": playback " + (value ? "suspended" : "restored"));
        }

        /// <summary>
        /// Recomputes the pause state per monitor.
        ///
        /// Global reasons (lock screen, battery, the user's own pause) stop every
        /// display. A fullscreen or maximized window stops only the displays it
        /// actually covers, so a game on one monitor no longer freezes the
        /// wallpaper on the others.
        /// </summary>
        private void ApplyPauseState()
        {
            bool battery = config.PauseOnBattery && Forms.SystemInformation.PowerStatus.PowerLineStatus == Forms.PowerLineStatus.Offline;
            bool globalPause = userPaused || systemIdle || battery;

            // One call, so a monitor that must resume and one that must pause are
            // updated together - no intermediate state where everything runs.
            var covered = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (!globalPause)
            {
                if (config.PauseFullscreen)
                    foreach (string device in NativeDesktop.FindCoveredMonitors()) covered.Add(device);
                if (config.PauseMaximized)
                    foreach (string device in NativeDesktop.FindMaximizedMonitors()) covered.Add(device);
            }
            manager.ApplyPauseState(covered, globalPause);
        }

        private void OnHealthTick(object sender, EventArgs e)
        {
            ApplyPauseState();
            // Self-healing: an Explorer restart or a rival wallpaper tool can
            // destroy the WorkerW the videos are parented to, which leaves a
            // black desktop behind a perfectly healthy-looking process.
            manager.VerifyDesktopHosts();
            string signature = GetMonitorSignature();
            if (signature != lastMonitorSignature)
            {
                lastMonitorSignature = signature;
                manager.CloseAll();
                RestoreWallpapers();
                ShowToast(Forms.Screen.AllScreens.Length + " " + Tr("apply.screens"));
                if (activePage == "displays") SwitchPage("displays");
            }
            if (activePage == "performance") UpdateTelemetry();
        }

        private static string GetMonitorSignature()
        {
            return string.Join("|", Forms.Screen.AllScreens.OrderBy(s => s.DeviceName, StringComparer.OrdinalIgnoreCase).Select(s => s.DeviceName + ":" + s.Bounds.ToString()));
        }

        private static Forms.Screen[] OrderedScreens()
        {
            return Forms.Screen.AllScreens.OrderByDescending(s => s.Primary).ThenBy(s => s.Bounds.Left).ThenBy(s => s.Bounds.Top).ToArray();
        }

        private void SetupTray()
        {
            Drawing.Icon appIcon = Drawing.Icon.ExtractAssociatedIcon(Process.GetCurrentProcess().MainModule.FileName);
            tray = new Forms.NotifyIcon { Text = "LumaWall", Icon = appIcon ?? Drawing.SystemIcons.Application, Visible = true };
            tray.DoubleClick += delegate { ShowFromTray(); };
            var menu = new Forms.ContextMenuStrip();
            menu.Items.Add("Buka LumaWall", null, delegate { ShowFromTray(); });
            menu.Items.Add("Pause / Lanjut", null, delegate
            {
                userPaused = !userPaused;
                // Apply immediately instead of waiting for the next 2s health tick,
                // which made the tray toggle feel broken for up to two seconds.
                ApplyPauseState();
                ShowToast(userPaused ? "Wallpaper dijeda" : "Wallpaper dilanjutkan");
            });
            menu.Items.Add("Keluar", null, delegate { ExitApp(); });
            tray.ContextMenuStrip = menu;
        }

        private void ShowFromTray() { ShowInTaskbar = true; Show(); WindowState = WindowState.Normal; Activate(); }
        private void OnClosing(object sender, System.ComponentModel.CancelEventArgs e) { if (!exiting) { e.Cancel = true; ShowInTaskbar = false; Hide(); } }
        private void ExitApp() { exiting = true; healthTimer.Stop(); RemoveForegroundHook(); manager.CloseAll(); tray.Visible = false; tray.Dispose(); Application.Current.Shutdown(); }

        private void ShowToast(string message)
        {
            toastText.Text = message;
            toast.Visibility = Visibility.Visible;
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
            timer.Tick += delegate { timer.Stop(); toast.Visibility = Visibility.Collapsed; };
            timer.Start();
        }

        // ================= LAYOUT HELPERS =================

        private static StackPanel PageCanvas() { return new StackPanel { Margin = new Thickness(30, 26, 30, 38) }; }

        private static ScrollViewer PageScroll(UIElement content) { return new ScrollViewer { Content = content, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled }; }

        private Grid PageHeading(string title, string subtitle, UIElement action)
        {
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var copy = new StackPanel();
            copy.Children.Add(new TextBlock { Text = title, Foreground = new SolidColorBrush(CText), FontFamily = FDisplay, FontSize = 26, FontWeight = FontWeights.SemiBold });
            copy.Children.Add(new TextBlock { Text = subtitle, Foreground = new SolidColorBrush(CMuted), FontSize = 12.5, Margin = new Thickness(0, 7, 0, 0) });
            grid.Children.Add(copy);
            if (action != null)
            {
                var element = action as FrameworkElement;
                if (element != null) element.VerticalAlignment = VerticalAlignment.Center;
                Grid.SetColumn(action, 1);
                grid.Children.Add(action);
            }
            return grid;
        }

        private UIElement SectionHeader(string title, string action, RoutedEventHandler click)
        {
            var grid = new Grid { Margin = new Thickness(0, 26, 0, 12) };
            grid.ColumnDefinitions.Add(new ColumnDefinition());
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var head = new StackPanel { Orientation = Orientation.Horizontal };
            head.Children.Add(new Border { Width = 3, Height = 16, CornerRadius = new CornerRadius(2), Background = new SolidColorBrush(CPrimary), VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 10, 0) });
            head.Children.Add(new TextBlock { Text = title, Foreground = new SolidColorBrush(CText), FontSize = 16, FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center });
            grid.Children.Add(head);
            var button = new Button { Content = action, Foreground = new SolidColorBrush(CPrimaryHi), Background = Brushes.Transparent, BorderThickness = new Thickness(0), Cursor = Cursors.Hand, FontSize = 12 };
            // Same reason as the settings toggle: the default template's hover is a
            // pale blue that does not belong in this palette.
            SetRoundedButton(button, 5);
            button.Click += click;
            Grid.SetColumn(button, 1);
            grid.Children.Add(button);
            return grid;
        }

        private Border SurfaceCard(Thickness margin)
        {
            return new Border { Margin = margin, CornerRadius = new CornerRadius(10), Background = new SolidColorBrush(CSurface), BorderBrush = new SolidColorBrush(CBorder), BorderThickness = new Thickness(1), ClipToBounds = true };
        }

        private Border EmptyCard(string title, string subtitle)
        {
            var b = SurfaceCard(new Thickness(0, 16, 16, 16));
            b.Width = 440;
            b.Height = 158;
            var s = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center };
            s.Children.Add(Icons.Build(Icons.Empty, 24, new SolidColorBrush(CDim)));
            s.Children.Add(new TextBlock { Text = title, Foreground = new SolidColorBrush(CText), FontSize = 14, FontWeight = FontWeights.SemiBold, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 10, 0, 0) });
            s.Children.Add(new TextBlock { Text = subtitle, Foreground = new SolidColorBrush(CMuted), FontSize = 11, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 5, 0, 0) });
            b.Child = s;
            return b;
        }

        private Border SettingGroup(string title, string subtitle, UIElement control)
        {
            var b = SurfaceCard(new Thickness(0, 22, 0, 0));
            var grid = new Grid { Margin = new Thickness(22, 20, 22, 20) };
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var copy = new StackPanel { MaxWidth = 460, HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Top };
            copy.Children.Add(new TextBlock { Text = title, Foreground = new SolidColorBrush(CText), FontSize = 15, FontWeight = FontWeights.SemiBold });
            copy.Children.Add(new TextBlock { Text = subtitle, Foreground = new SolidColorBrush(CMuted), FontSize = 11.5, Margin = new Thickness(0, 6, 0, 0), TextWrapping = TextWrapping.Wrap, LineHeight = 17 });
            grid.Children.Add(copy);
            var controlHost = new StackPanel { VerticalAlignment = VerticalAlignment.Top };
            controlHost.Children.Add(control);
            Grid.SetColumn(controlHost, 1);
            grid.Children.Add(controlHost);
            b.Child = grid;
            return b;
        }

        private Button PrimaryButton(string iconName, string text)
        {
            var stack = new StackPanel { Orientation = Orientation.Horizontal };
            stack.Children.Add(Icons.Build(iconName, 12, Brushes.White));
            stack.Children.Add(new TextBlock { Text = text, Foreground = Brushes.White, FontSize = 12, Margin = new Thickness(8, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center, FontWeight = FontWeights.SemiBold });
            var b = new Button
            {
                Content = stack,
                Height = 38,
                Padding = new Thickness(17, 0, 17, 0),
                Background = new SolidColorBrush(CPrimary),
                Foreground = Brushes.White,
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand,
                VerticalAlignment = VerticalAlignment.Center,
                FontWeight = FontWeights.SemiBold,
                Effect = new DropShadowEffect { Color = CPrimary, BlurRadius = 14, ShadowDepth = 0, Opacity = .5 }
            };
            b.MouseEnter += delegate { b.Background = new SolidColorBrush(CPrimaryHi); };
            b.MouseLeave += delegate { b.Background = new SolidColorBrush(CPrimary); };
            SetRoundedButton(b, 7);
            return b;
        }

        private Button GhostButton(string text)
        {
            var b = new Button
            {
                Content = text,
                Height = 38,
                Padding = new Thickness(15, 0, 15, 0),
                Background = new SolidColorBrush(CSurface2),
                Foreground = new SolidColorBrush(CText),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand,
                VerticalAlignment = VerticalAlignment.Center,
                FontSize = 12
            };
            b.MouseEnter += delegate { b.Background = new SolidColorBrush(CSurfaceHover); b.BorderBrush = new SolidColorBrush(CBorderHot); };
            b.MouseLeave += delegate { b.Background = new SolidColorBrush(CSurface2); b.BorderBrush = new SolidColorBrush(CBorder); };
            SetRoundedButton(b, 7);
            return b;
        }

        private Button IconButton(string icon, string tooltip)
        {
            var button = new Button
            {
                Content = Icons.Build(IconNameFor(icon), 13, new SolidColorBrush(CText)),
                ToolTip = tooltip,
                Width = 40,
                Height = 38,
                Background = new SolidColorBrush(CSurface2),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand
            };
            System.Windows.Automation.AutomationProperties.SetName(button, tooltip);
            SetRoundedButton(button, 7);
            return button;
        }

        private Button CompactActionButton(string text)
        {
            var button = new Button
            {
                Content = text,
                Height = 31,
                MinWidth = 64,
                Padding = new Thickness(12, 0, 12, 0),
                Background = new SolidColorBrush(CSurface2),
                Foreground = new SolidColorBrush(CText),
                BorderBrush = new SolidColorBrush(CBorder),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand,
                FontSize = 10.5,
                FontWeight = FontWeights.SemiBold,
                HorizontalContentAlignment = HorizontalAlignment.Center,
                VerticalContentAlignment = VerticalAlignment.Center
            };
            button.MouseEnter += delegate { button.Background = new SolidColorBrush(CPrimary); button.BorderBrush = new SolidColorBrush(CPrimary); button.Foreground = Brushes.White; };
            button.MouseLeave += delegate { button.Background = new SolidColorBrush(CSurface2); button.BorderBrush = new SolidColorBrush(CBorder); button.Foreground = new SolidColorBrush(CText); };
            SetRoundedButton(button, 6);
            return button;
        }

        /// <summary>
        /// Legacy call sites pass Segoe Fluent code points; they are mapped onto
        /// the hand-built vector icon set so no screen depends on an icon font.
        /// </summary>
        private static FrameworkElement Glyph(string code, double size, Brush color)
        {
            return Icons.Build(IconNameFor(code), size, color);
        }

        private static string IconNameFor(string code)
        {
            switch (code)
            {
                case "\uE80F": return Icons.Dashboard;
                case "\uE8F1": return Icons.Library;
                case "\uE774": return Icons.Catalog;
                case "\uE7F4": return Icons.Displays;
                case "\uE945": return Icons.Performance;
                case "\uE721": return Icons.Search;
                case "\uE710": return Icons.Add;
                case "\uE768": return Icons.Apply;
                case "\uE896": return Icons.Download;
                case "\uE71A": return Icons.Stop;
                case "\uE950": return Icons.Cpu;
                case "\uE964": return Icons.Memory;
                case "\uE7BA": return Icons.Warning;
                case "\uE7C3": return Icons.Empty;
                case "\uE73E": return Icons.Check;
                case "\uE74E": return Icons.Save;
                case "\uE8B9": return Icons.AllDisplays;
                case "\uE8BB": return Icons.Close;
                case "\uE921": return Icons.Minimize;
                case "\uE922": return Icons.Maximize;
                case "\uE923": return Icons.Restore;
                case "\uE72C": return Icons.Optimize;
                default: return Icons.Wallpaper;
            }
        }

        private static bool ComesFromButton(object source, DependencyObject stopAt)
        {
            DependencyObject current = source as DependencyObject;
            while (current != null && current != stopAt)
            {
                if (current is Button) return true;
                current = VisualTreeHelper.GetParent(current);
            }
            return false;
        }

        /// <summary>
        /// In-app brand mark: the chamfered "L" on a crimson -> white -> cyan
        /// diagonal, over a dark squircle plate.
        ///
        /// Same outline and same ramp as mark_outline() in make_store_assets.py,
        /// so the title bar, the .ico, the taskbar, the installer and the Store
        /// tiles cannot drift apart.
        /// </summary>
        private static UIElement BuildLogoMark(double size)
        {
            // Must stay equal to squircle_mask(radius_ratio) in make_store_assets.py.
            const double plateRadius = 0.235;
            var root = new Grid { Width = size, Height = size };

            // Plate: the dark squircle the icon generator paints first.
            root.Children.Add(new Border
            {
                CornerRadius = new CornerRadius(size * plateRadius),
                Background = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0),
                    EndPoint = new Point(0, 1),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromRgb(16, 19, 26), 0),
                        new GradientStop(Color.FromRgb(7, 8, 11), 1)
                    }
                },
                BorderBrush = new SolidColorBrush(Color.FromArgb(38, 255, 255, 255)),
                BorderThickness = new Thickness(1)
            });

            // The "L", mirrored from mark_outline() in the generator: bold strokes,
            // 45-degree chamfers on the outer corners, sharp inner corner.
            //
            // The span must match the icon: mark_outline draws the L across 0.76
            // of whatever span it gets, and the generated icons use
            // PAD_PLATED = 0.06, so span = 0.94 puts the in-app mark at the same
            // 71% of the tile the .ico and the Store tiles use. A hard-coded 0.70
            // here left the title-bar L at 53% - noticeably smaller than the L in
            // the taskbar, which is what made the two look like different logos.
            const double span = 0.94;
            double s = size * span;
            double cx = size / 2.0, cy = size / 2.0;
            Func<double, double, Point> pt = (x, y) => new Point(cx + x * s, cy + y * s);
            var mark = new System.Windows.Shapes.Polygon
            {
                Points = new PointCollection
                {
                    pt(-0.24, -0.38),
                    pt(-0.08, -0.38),
                    pt(-0.08, 0.08),
                    pt(0.38, 0.08),
                    pt(0.38, 0.24),
                    pt(0.24, 0.38),
                    pt(-0.38, 0.38),
                    pt(-0.38, -0.24)
                },
                // One brush across the whole mark so the ramp runs corner to corner
                // exactly like the generated icon.
                Fill = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0),
                    EndPoint = new Point(1, 1),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(CPrimary, 0.00),
                        new GradientStop(CPrimaryHi, 0.28),
                        new GradientStop(Color.FromRgb(255, 238, 244), 0.50),
                        new GradientStop(Color.FromRgb(124, 233, 252), 0.72),
                        new GradientStop(CAccent, 1.00)
                    }
                }
            };
            root.Children.Add(mark);
            return root;
        }

        private static void SetRoundedButton(Button button, double radius)
        {
            var border = new FrameworkElementFactory(typeof(Border));
            border.SetBinding(Border.BackgroundProperty, new Binding("Background") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.BorderBrushProperty, new Binding("BorderBrush") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.BorderThicknessProperty, new Binding("BorderThickness") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetBinding(Border.PaddingProperty, new Binding("Padding") { RelativeSource = RelativeSource.TemplatedParent });
            border.SetValue(Border.CornerRadiusProperty, new CornerRadius(radius));
            var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
            presenter.SetBinding(ContentPresenter.ContentProperty, new Binding("Content") { RelativeSource = RelativeSource.TemplatedParent });
            presenter.SetBinding(ContentPresenter.HorizontalAlignmentProperty, new Binding("HorizontalContentAlignment") { RelativeSource = RelativeSource.TemplatedParent });
            presenter.SetBinding(ContentPresenter.VerticalAlignmentProperty, new Binding("VerticalContentAlignment") { RelativeSource = RelativeSource.TemplatedParent });
            border.AppendChild(presenter);
            button.Template = new ControlTemplate(typeof(Button)) { VisualTree = border };
        }

        private static string FormatBytes(long bytes)
        {
            if (bytes >= 1024L * 1024L * 1024L) return (bytes / (1024d * 1024d * 1024d)).ToString("0.0") + " GB";
            if (bytes >= 1024L * 1024L) return (bytes / (1024d * 1024d)).ToString("0.0") + " MB";
            return (bytes / 1024d).ToString("0") + " KB";
        }

        private static bool IsImageFile(string path)
        {
            string extension = Path.GetExtension(path).ToLowerInvariant();
            return extension == ".jpg" || extension == ".jpeg" || extension == ".png" || extension == ".bmp" || extension == ".webp";
        }

        private static string FindFfmpeg()
        {
            string local = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ffmpeg.exe");
            if (File.Exists(local)) return local;
            foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
            {
                try { string candidate = Path.Combine(folder.Trim(), "ffmpeg.exe"); if (File.Exists(candidate)) return candidate; } catch { }
            }
            return null;
        }

        /// <summary>
        /// Enables or disables "start with Windows".
        ///
        /// Two mechanisms are needed because the app ships both as a classic
        /// installer and as an MSIX package:
        ///
        ///   * MSIX: writes to HKCU\...\Run are virtualised into the package's
        ///     private hive. The value is stored, the toggle looks like it
        ///     worked, and Windows never runs the app - the feature is silently
        ///     broken. A packaged app must ask the StartupTask API instead, which
        ///     also makes it appear in Settings > Apps > Startup.
        ///
        ///   * Classic install: there is no package identity, so the StartupTask
        ///     API is unavailable and the Run key is the correct mechanism.
        /// </summary>
        private static void SetStartup(bool enabled)
        {
            if (TrySetPackagedStartup(enabled)) return;
            SetRegistryStartup(enabled);
        }

        // ── package identity ──────────────────────────────────────────────
        private const int ERROR_INSUFFICIENT_BUFFER = 122;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetCurrentPackageFullName(ref int packageFullNameLength, StringBuilder packageFullName);

        /// <summary>
        /// True when the process runs with MSIX package identity.
        ///
        /// The call returns ERROR_INSUFFICIENT_BUFFER (and the required size)
        /// exactly when a package identity exists; an unpackaged process reports
        /// APPMODEL_ERROR_NO_PACKAGE instead.
        /// </summary>
        private static bool IsPackaged()
        {
            try
            {
                int length = 0;
                return GetCurrentPackageFullName(ref length, null) == ERROR_INSUFFICIENT_BUFFER;
            }
            catch { return false; }
        }

        // ── WinRT activation through its ABI ──────────────────────────────
        // The SDK projection cannot be consumed by this toolchain (see the class
        // comment), so the API is reached through combase and raw vtable slots.
        // The first parameter is an HSTRING handle, not a character pointer:
        // marshalling a string here produces E_INVALIDARG before the class is
        // even examined. Build the HSTRING with WindowsCreateString instead.
        [DllImport("combase.dll")]
        private static extern int RoGetActivationFactory(IntPtr activatableClassId, ref Guid iid, out IntPtr factory);

        [DllImport("combase.dll", CharSet = CharSet.Unicode)]
        private static extern int WindowsCreateString(string source, int length, out IntPtr hstring);

        [DllImport("combase.dll")]
        private static extern int WindowsDeleteString(IntPtr hstring);

        // IIDs read from the Windows SDK header (windows.applicationmodel.h).
        private static readonly Guid IID_IStartupTaskStatics = new Guid("ee5b60bd-a148-41a7-b26e-e8b88a1e62f8");
        private static readonly Guid IID_IStartupTask = new Guid("f75c23c8-b5f2-4f6c-88dd-36cb1d599d17");

        // vtable slots. IInspectable occupies 0..5 (IUnknown 0..2, then GetIids,
        // GetRuntimeClassName, GetTrustLevel), so the first real method is 6.
        private const int Slot_GetAsync = 7;              // IStartupTaskStatics
        private const int Slot_RequestEnableAsync = 6;    // IStartupTask
        private const int Slot_Disable = 7;               // IStartupTask
        private const int Slot_get_State = 8;             // IStartupTask
        private const int Slot_GetResults = 5;            // IAsyncOperation<T>
        private const int Slot_get_Status = 6;            // IAsyncOperation<T>

        /// <summary>
        /// Activates a WinRT runtime class and returns its activation factory.
        ///
        /// The class name has to be passed as a real HSTRING; marshalling a C#
        /// string into that parameter yields E_INVALIDARG.
        /// </summary>
        private static int ActivateFactory(string className, Guid iid, out IntPtr factory)
        {
            factory = IntPtr.Zero;
            IntPtr classId = IntPtr.Zero;
            try
            {
                if (WindowsCreateString(className, className.Length, out classId) != 0) return -1;
                return RoGetActivationFactory(classId, ref iid, out factory);
            }
            finally
            {
                if (classId != IntPtr.Zero) WindowsDeleteString(classId);
            }
        }

        private const int AsyncStatusCompleted = 1;

        // StartupTaskState values.
        private const int StartupDisabled = 0;
        private const int StartupEnabled = 1;
        private const int StartupDisabledByUser = 2;
        private const int StartupDisabledByPolicy = 3;
        private const int StartupEnabledByPolicy = 4;

        private delegate int GetAsyncDelegate(IntPtr self, IntPtr taskId, out IntPtr operation);
        private delegate int RequestEnableAsyncDelegate(IntPtr self, out IntPtr operation);
        private delegate int DisableDelegate(IntPtr self);
        private delegate int GetStateDelegate(IntPtr self, out int state);
        private delegate int GetResultsDelegate(IntPtr self, out IntPtr result);

        /// <summary>Invokes a vtable slot as a typed delegate.</summary>
        private static T Vtable<T>(IntPtr obj, int slot) where T : class
        {
            IntPtr vtable = Marshal.ReadIntPtr(obj);
            IntPtr fn = Marshal.ReadIntPtr(vtable, slot * IntPtr.Size);
            return (T)(object)Marshal.GetDelegateForFunctionPointer(fn, typeof(T));
        }

        /// <summary>
        /// Enables/disables the manifest's startupTask. Returns false when the
        /// app is not packaged, so the caller can fall back to the registry.
        /// </summary>
        private static bool TrySetPackagedStartup(bool enabled)
        {
            if (!IsPackaged()) return false;

            IntPtr factory = IntPtr.Zero, taskId = IntPtr.Zero, task = IntPtr.Zero;
            try
            {
                Guid iid = IID_IStartupTaskStatics;
                int hr = ActivateFactory("Windows.ApplicationModel.StartupTask", iid, out factory);
                if (hr != 0 || factory == IntPtr.Zero)
                {
                    AppLog.Write("StartupTask activation failed (hr=0x" + hr.ToString("X8") + "); using the Run key");
                    return false;
                }

                if (WindowsCreateString("LumaWallStartup", 15, out taskId) != 0) return false;

                IntPtr operation = IntPtr.Zero;
                hr = Vtable<GetAsyncDelegate>(factory, Slot_GetAsync)(factory, taskId, out operation);
                if (hr != 0 || operation == IntPtr.Zero)
                {
                    AppLog.Write("StartupTask.GetAsync failed (hr=0x" + hr.ToString("X8") + ")");
                    return false;
                }

                hr = Resolve(operation, out task);
                if (hr != 0 || task == IntPtr.Zero)
                {
                    AppLog.Write("StartupTask lookup returned nothing (hr=0x" + hr.ToString("X8") + ")");
                    return false;
                }

                if (enabled)
                {
                    IntPtr op2 = IntPtr.Zero;
                    hr = Vtable<RequestEnableAsyncDelegate>(task, Slot_RequestEnableAsync)(task, out op2);
                    if (hr != 0 || op2 == IntPtr.Zero)
                    {
                        AppLog.Write("StartupTask.RequestEnableAsync failed (hr=0x" + hr.ToString("X8") + ")");
                        return false;
                    }
                    IntPtr statePtr;
                    hr = Resolve(op2, out statePtr);
                    int state = hr == 0 ? statePtr.ToInt32() : -1;
                    AppLog.Write("MSIX startup task requested; state=" + state);
                    if (state == StartupDisabledByUser)
                        AppLog.Write("Startup is disabled by the user in Windows settings and must be re-enabled there");
                }
                else
                {
                    hr = Vtable<DisableDelegate>(task, Slot_Disable)(task);
                    AppLog.Write("MSIX startup task disabled (hr=0x" + hr.ToString("X8") + ")");
                }
                return true;
            }
            catch (Exception ex)
            {
                AppLog.Write("StartupTask call failed (" + ex.Message + "); using the Run key");
                return false;
            }
            finally
            {
                if (task != IntPtr.Zero) Marshal.Release(task);
                if (factory != IntPtr.Zero) Marshal.Release(factory);
                if (taskId != IntPtr.Zero) WindowsDeleteString(taskId);
            }
        }

        /// <summary>
        /// Waits for a WinRT IAsyncOperation and returns its result.
        ///
        /// GetResults blocks until the operation completes, but returns
        /// E_ILLEGAL_METHOD_CALL while it is still running, so a bounded retry
        /// loop keeps this safe from a synchronous caller without needing the
        /// async completion handler machinery.
        /// </summary>
        private static int Resolve(IntPtr operation, out IntPtr result)
        {
            result = IntPtr.Zero;
            for (int attempt = 0; attempt < 200; attempt++)   // up to ~10 s
            {
                try
                {
                    int hr = Vtable<GetResultsDelegate>(operation, Slot_GetResults)(operation, out result);
                    if (hr == 0) return 0;
                    // E_ILLEGAL_METHOD_CALL = still running.
                    if (hr != unchecked((int)0x8000000EL)) return hr;
                }
                catch (Exception ex)
                {
                    AppLog.Write("Waiting for a WinRT operation failed: " + ex.Message);
                    return -1;
                }
                System.Threading.Thread.Sleep(50);
            }
            AppLog.Write("WinRT operation timed out");
            return -1;
        }

        /// <summary>
        /// Classic (non-packaged) autostart via HKCU\...\Run.
        ///
        /// The value carries --background so a Windows-triggered launch goes
        /// straight to the tray with the wallpaper already running, instead of
        /// opening the window over whatever the user is doing at login.
        /// </summary>
        private static void SetRegistryStartup(bool enabled)
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run", true))
                {
                    if (key == null) return;
                    if (enabled) key.SetValue("LumaWall", "\"" + Process.GetCurrentProcess().MainModule.FileName + "\" --background");
                    else key.DeleteValue("LumaWall", false);
                }
            }
            catch (Exception ex) { AppLog.Write("Could not update the Run key: " + ex.Message); }
        }

        private static bool IsStartupEnabled()
        {
            // Under MSIX the authoritative source is the startup task, not the
            // (virtualised) registry value: reading the registry there reports
            // the opposite of what Windows will actually do.
            if (IsPackaged())
            {
                IntPtr factory = IntPtr.Zero, taskId = IntPtr.Zero, task = IntPtr.Zero;
                try
                {
                    Guid iid = IID_IStartupTaskStatics;
                    IntPtr operation = IntPtr.Zero;
                    if (ActivateFactory("Windows.ApplicationModel.StartupTask", iid, out factory) == 0 && factory != IntPtr.Zero &&
                        WindowsCreateString("LumaWallStartup", 15, out taskId) == 0 &&
                        Vtable<GetAsyncDelegate>(factory, Slot_GetAsync)(factory, taskId, out operation) == 0 &&
                        Resolve(operation, out task) == 0 && task != IntPtr.Zero)
                    {
                        int state;
                        if (Vtable<GetStateDelegate>(task, Slot_get_State)(task, out state) == 0)
                            return state == StartupEnabled || state == StartupEnabledByPolicy;
                    }
                }
                catch (Exception ex) { AppLog.Write("Could not read the startup task state: " + ex.Message); }
                finally
                {
                    if (task != IntPtr.Zero) Marshal.Release(task);
                    if (factory != IntPtr.Zero) Marshal.Release(factory);
                    if (taskId != IntPtr.Zero) WindowsDeleteString(taskId);
                }
            }

            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run", false))
                    return key != null && key.GetValue("LumaWall") != null;
            }
            catch { return false; }
        }
    }
}
