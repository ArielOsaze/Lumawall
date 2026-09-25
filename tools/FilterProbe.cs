// FilterProbe.cs - runs the pause detector's own filter logic and reports the
// decision for each window, so a wrong verdict can be traced to the exact rule
// that produced it.
//
// The app's filter lives in NativeDesktop (Program.cs). Rather than guess why a
// window was ignored, this reproduces the same rules and prints each one.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class FilterProbe
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);

    private delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

    private const long WS_EX_TOOLWINDOW = 0x00000080L;
    private const long WS_EX_NOACTIVATE = 0x08000000L;
    private const long WS_EX_TRANSPARENT = 0x00000020L;

    private static string Cls(IntPtr h) { var s = new StringBuilder(200); GetClassName(h, s, s.Capacity); return s.ToString(); }
    private static string Ttl(IntPtr h) { var s = new StringBuilder(256); GetWindowText(h, s, s.Capacity); return s.ToString(); }

    private static bool IsShellProcess(IntPtr hwnd)
    {
        try
        {
            uint pid; GetWindowThreadProcessId(hwnd, out pid);
            if (pid == 0) return false;
            string name;
            using (var p = Process.GetProcessById((int)pid)) name = p.ProcessName;
            if (string.IsNullOrEmpty(name)) return false;
            return name == "ShellExperienceHost" || name == "StartMenuExperienceHost" ||
                   name == "SearchHost" || name == "SearchApp" || name == "TextInputHost" ||
                   name == "LockApp" || name == "ShellHost" || name == "explorer";
        }
        catch { return false; }
    }

    private static bool IsOverlayWindow(IntPtr hwnd)
    {
        string value = Cls(hwnd);
        if (value.Length == 0) return true;
        if (IsShellProcess(hwnd)) return true;
        if (value == "CEF-OSC-WIDGET" || value == "TextInputHost" ||
            value.StartsWith("Windows.UI.Composition", StringComparison.Ordinal) ||
            value.StartsWith("Cua.", StringComparison.Ordinal) ||
            value == "XamlExplorerHostIslandWindow") return true;
        if (Ttl(hwnd).Length == 0) return true;
        return false;
    }

    private static bool IsNonAppWindow(IntPtr hwnd)
    {
        long ex = GetWindowLongPtr64(hwnd, -20).ToInt64();
        if ((ex & WS_EX_TOOLWINDOW) != 0) return true;
        if ((ex & WS_EX_NOACTIVATE) != 0) return true;
        if ((ex & WS_EX_TRANSPARENT) != 0) return true;
        if (Cls(hwnd).Length == 0) return true;
        return false;
    }

    private static int Main()
    {
        int ownPid = -1;
        foreach (var p in Process.GetProcessesByName("LumaWall")) ownPid = p.Id;
        Console.WriteLine("LumaWall pid: " + ownPid);
        Console.WriteLine();
        Console.WriteLine("  window                                    vis icon  verdict        reason");
        Console.WriteLine("  ----------------------------------------- --- ---- -------------- ------------------------");

        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            string cls = Cls(h);
            string title = Ttl(h);
            // Show anything that looks like an app or a shell surface.
            bool interesting = cls == "Windows.UI.Core.CoreWindow" || cls == "ApplicationFrameWindow" ||
                               cls.StartsWith("Chrome_WidgetWin") || cls == "TaskManagerWindow";
            if (!interesting) return true;

            uint pid; GetWindowThreadProcessId(h, out pid);
            string procName = "?";
            try { procName = Process.GetProcessById((int)pid).ProcessName; } catch { }

            bool visible = IsWindowVisible(h);
            bool iconic = IsIconic(h);

            string verdict, reason;
            if (!visible) { verdict = "skip"; reason = "not visible"; }
            else if (iconic) { verdict = "skip"; reason = "minimized"; }
            else if (pid == (uint)ownPid) { verdict = "skip"; reason = "own window"; }
            else if (IsOverlayWindow(h)) { verdict = "IGNORED"; reason = "IsOverlayWindow"; }
            else if (IsNonAppWindow(h)) { verdict = "IGNORED"; reason = "IsNonAppWindow"; }
            else { verdict = "CONSIDERED"; reason = "-"; }

            RECT r; GetWindowRect(h, out r);
            int w = r.R - r.L, ht = r.B - r.T;

            // Does it cover a monitor?
            string covers = "none";
            foreach (var s in System.Windows.Forms.Screen.AllScreens)
            {
                var b = s.Bounds;
                int ow = Math.Min(r.R, b.Right) - Math.Max(r.L, b.Left);
                int oh = Math.Min(r.B, b.Bottom) - Math.Max(r.T, b.Top);
                if (ow >= b.Width * 0.98 && oh >= b.Height * 0.98)
                    covers = s.DeviceName;
            }

            string label = (cls.Length > 24 ? cls.Substring(0, 24) : cls) + " " + procName;
            if (label.Length > 41) label = label.Substring(0, 41);

            Console.WriteLine(string.Format("  {0,-41} {1,-3} {2,-4} {3,-14} {4}   [{5}x{6}] covers={7}",
                label, visible ? "yes" : "no", iconic ? "yes" : "no", verdict, reason, w, ht, covers));
            return true;
        }, IntPtr.Zero);

        return 0;
    }
}
