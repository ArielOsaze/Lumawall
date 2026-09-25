// DiagnoseWallpaperWindows.cs - why is the desktop black when the video is
// playing?
//
// The log shows "Seamless loop handoff completed", so WebView2 is decoding and
// looping. That means the window exists and is alive, but is not visible. This
// prints the exact geometry, z-order and styles of every LumaWall window so the
// reason (wrong position, zero size, hidden, behind an opaque sibling) becomes
// a measurement instead of a guess.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class DiagnoseWallpaperWindows
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr h, uint f);
    [DllImport("user32.dll")] private static extern IntPtr FindWindow(string c, string t);
    [DllImport("user32.dll")] private static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);
    [DllImport("user32.dll")] private static extern IntPtr GetWindow(IntPtr h, uint cmd);

    private delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

    private const uint GW_HWNDNEXT = 2;

    private static string Cls(IntPtr h)
    {
        var sb = new StringBuilder(200);
        GetClassName(h, sb, sb.Capacity);
        return sb.ToString();
    }

    private static int Main()
    {
        int lumaPid = -1;
        foreach (var p in Process.GetProcessesByName("LumaWall")) lumaPid = p.Id;
        Console.WriteLine("LumaWall pid: " + lumaPid);

        IntPtr progman = FindWindow("Progman", null);
        Console.WriteLine("Progman: 0x" + progman.ToInt64().ToString("X") + "  visible=" + IsWindowVisible(progman));
        RECT pr;
        GetWindowRect(progman, out pr);
        Console.WriteLine("  window rect: (" + pr.L + "," + pr.T + ") " + (pr.R - pr.L) + "x" + (pr.B - pr.T));
        RECT pc;
        GetClientRect(progman, out pc);
        Console.WriteLine("  client rect: " + (pc.R - pc.L) + "x" + (pc.B - pc.T));

        Console.WriteLine();
        Console.WriteLine("=== children of Progman, in Z-ORDER (first = topmost) ===");
        int index = 0;
        IntPtr child = FindWindowEx(progman, IntPtr.Zero, null, null);
        while (child != IntPtr.Zero)
        {
            RECT r;
            GetWindowRect(child, out r);
            uint pid;
            GetWindowThreadProcessId(child, out pid);
            long ex = GetWindowLongPtr64(child, -20).ToInt64();
            long st = GetWindowLongPtr64(child, -16).ToInt64();
            Console.WriteLine(string.Format(
                "  [{0}] 0x{1:X8} {2,-42} rect=({3},{4}) {5}x{6} vis={7} pid={8} ex=0x{9:X} style=0x{10:X}",
                index++, child.ToInt64(), Cls(child), r.L, r.T, r.R - r.L, r.B - r.T,
                IsWindowVisible(child), pid, ex, st));
            child = FindWindowEx(progman, child, null, null);
        }

        Console.WriteLine();
        Console.WriteLine("=== every window owned by LumaWall, with REAL parent ===");
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            uint pid;
            GetWindowThreadProcessId(h, out pid);
            if (pid != (uint)lumaPid) return true;
            RECT r;
            GetWindowRect(h, out r);
            Console.WriteLine(string.Format(
                "  0x{0:X8} {1,-42} rect=({2},{3}) {4}x{5} vis={6}",
                h.ToInt64(), Cls(h), r.L, r.T, r.R - r.L, r.B - r.T, IsWindowVisible(h)));
            // recurse one level for the WebView2 tree
            IntPtr c = FindWindowEx(h, IntPtr.Zero, null, null);
            while (c != IntPtr.Zero)
            {
                RECT cr;
                GetWindowRect(c, out cr);
                Console.WriteLine(string.Format(
                    "      child 0x{0:X8} {1,-38} rect=({2},{3}) {4}x{5} vis={6}",
                    c.ToInt64(), Cls(c), cr.L, cr.T, cr.R - cr.L, cr.B - cr.T, IsWindowVisible(c)));
                c = FindWindowEx(h, c, null, null);
            }
            return true;
        }, IntPtr.Zero);

        Console.WriteLine();
        Console.WriteLine("=== screen geometry ===");
        foreach (var s in System.Windows.Forms.Screen.AllScreens)
            Console.WriteLine(string.Format("  {0} bounds=({1},{2}) {3}x{4} primary={5}",
                s.DeviceName, s.Bounds.X, s.Bounds.Y, s.Bounds.Width, s.Bounds.Height, s.Primary));
        Console.WriteLine();
        Console.WriteLine("Note: a child window's GetWindowRect is in SCREEN coordinates,");
        Console.WriteLine("      so a wallpaper on the primary display should read (0,0) 1920x1080.");
        return 0;
    }
}
