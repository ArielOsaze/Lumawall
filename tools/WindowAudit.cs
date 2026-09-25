// WindowAudit.cs - lists every top-level window and whether it covers a monitor.
//
// Motivation: the user reports fullscreen apps on every display while the GPU
// keeps decoding video. The pause detector only ever looks at
// GetForegroundWindow() - and Windows has exactly ONE foreground window, so a
// fullscreen app on a display that is not focused is never considered. This
// tool shows what is actually on screen, so the gap is measured rather than
// guessed.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class WindowAudit
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsZoomed(IntPtr h);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr h, uint f);

    private delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

    private const long WS_EX_TOOLWINDOW = 0x00000080L;
    private const long WS_EX_NOACTIVATE = 0x08000000L;
    private const long WS_EX_TRANSPARENT = 0x00000020L;

    private static string Cls(IntPtr h) { var sb = new StringBuilder(160); GetClassName(h, sb, sb.Capacity); return sb.ToString(); }
    private static string Title(IntPtr h) { var sb = new StringBuilder(160); GetWindowText(h, sb, sb.Capacity); return sb.ToString(); }

    private static int Main(string[] args)
    {
        int lumaPid = -1;
        foreach (var p in Process.GetProcessesByName("LumaWall")) lumaPid = p.Id;
        Console.WriteLine("LumaWall pid: " + lumaPid);

        IntPtr fg = GetForegroundWindow();
        uint fgPid; GetWindowThreadProcessId(fg, out fgPid);
        Console.WriteLine();
        Console.WriteLine("=== FOREGROUND WINDOW (the only one the detector examines) ===");
        Console.WriteLine("  hwnd 0x" + fg.ToInt64().ToString("X8") + "  pid " + fgPid);
        Console.WriteLine("  class: " + Cls(fg));
        Console.WriteLine("  title: " + Title(fg));
        RECT fr; GetWindowRect(fg, out fr);
        Console.WriteLine("  rect: (" + fr.L + "," + fr.T + ") " + (fr.R - fr.L) + "x" + (fr.B - fr.T));
        Console.WriteLine("  zoomed: " + IsZoomed(fg));

        Console.WriteLine();
        Console.WriteLine("=== MONITORS ===");
        foreach (var s in System.Windows.Forms.Screen.AllScreens)
            Console.WriteLine("  " + s.DeviceName + "  (" + s.Bounds.X + "," + s.Bounds.Y + ") " +
                              s.Bounds.Width + "x" + s.Bounds.Height + "  primary=" + s.Primary);

        Console.WriteLine();
        Console.WriteLine("=== EVERY VISIBLE TOP-LEVEL WINDOW THAT COVERS A MONITOR ===");
        Console.WriteLine("  (this is what the detector SHOULD be considering)");
        Console.WriteLine();

        var rows = new List<string>();
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            if (!IsWindowVisible(h)) return true;
            if (IsIconic(h)) return true;

            long ex = GetWindowLongPtr64(h, -20).ToInt64();
            if ((ex & WS_EX_TOOLWINDOW) != 0) return true;
            if ((ex & WS_EX_NOACTIVATE) != 0) return true;

            RECT r;
            if (!GetWindowRect(h, out r)) return true;
            int w = r.R - r.L, ht = r.B - r.T;
            if (w <= 0 || ht <= 0) return true;

            uint pid; GetWindowThreadProcessId(h, out pid);
            string cls = Cls(h);
            string title = Title(h);
            if (title.Length > 44) title = title.Substring(0, 41) + "...";

            bool isForeground = h == fg;
            bool isLuma = pid == (uint)lumaPid;

            // Which monitors does this window cover?
            var covers = new List<string>();
            foreach (var s in System.Windows.Forms.Screen.AllScreens)
            {
                var b = s.Bounds;
                int ow = Math.Min(r.R, b.Right) - Math.Max(r.L, b.Left);
                int oh = Math.Min(r.B, b.Bottom) - Math.Max(r.T, b.Top);
                if (ow >= b.Width * 0.98 && oh >= b.Height * 0.98) covers.Add(s.DeviceName);
            }

            // Only show windows that cover at least one full monitor, plus any
            // LumaWall window so its own state is visible.
            if (covers.Count == 0 && !isLuma) return true;

            rows.Add(string.Format("  {0}{1} {2,-34} {3,-24} covers={4}  pid={5}{6}",
                isForeground ? ">" : " ",
                IsZoomed(h) ? "Z" : " ",
                cls.Length > 34 ? cls.Substring(0, 34) : cls,
                title,
                covers.Count > 0 ? string.Join(",", covers) : "none",
                pid,
                isLuma ? "  <- LumaWall" : ""));
            return true;
        }, IntPtr.Zero);

        foreach (var row in rows) Console.WriteLine(row);

        Console.WriteLine();
        Console.WriteLine("=== INTERPRETATION ===");
        Console.WriteLine("  '>' marks the foreground window - the ONLY one the current");
        Console.WriteLine("  detector checks. Any other row with a 'covers=' list is a");
        Console.WriteLine("  fullscreen app the detector cannot see.");
        return 0;
    }
}
