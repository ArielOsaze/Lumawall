// InspectDesktop.cs - shows what actually happened to the wallpaper windows
// after an Explorer restart.
//
// The app logged "lost its desktop host, re-attaching" every 2 s without ever
// following it with "Desktop host attached", which means AttachToWallpaper is
// returning early or the window handle is no longer usable. This prints the raw
// window state so the reason is visible instead of guessed.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class InspectDesktop
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr h, uint f);
    [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr h);
    [DllImport("user32.dll")] private static extern IntPtr GetDesktopWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern IntPtr FindWindow(string c, string t);
    [DllImport("user32.dll")] private static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);

    private delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

    private static string Cls(IntPtr h)
    {
        var sb = new StringBuilder(128);
        GetClassName(h, sb, sb.Capacity);
        return sb.ToString();
    }

    private static int Main()
    {
        int lumaPid = -1;
        foreach (var p in Process.GetProcessesByName("LumaWall")) lumaPid = p.Id;
        Console.WriteLine("LumaWall pid: " + lumaPid);

        Console.WriteLine();
        Console.WriteLine("=== Desktop host chain ===");
        IntPtr progman = FindWindow("Progman", null);
        Console.WriteLine("Progman           : 0x" + progman.ToInt64().ToString("X") + "  alive=" + IsWindow(progman) + "  cls=" + Cls(progman));
        IntPtr workerUnderProgman = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
        Console.WriteLine("WorkerW under Progman: 0x" + workerUnderProgman.ToInt64().ToString("X") + "  alive=" + IsWindow(workerUnderProgman));

        Console.WriteLine();
        Console.WriteLine("=== All top-level WorkerW / SHELLDLL_DefView ===");
        var found = new List<string>();
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            string cls = Cls(h);
            if (cls == "WorkerW" || cls == "SHELLDLL_DefView")
            {
                IntPtr parent = GetParent(h);
                IntPtr anc = GetAncestor(h, 1);
                found.Add(string.Format("  0x{0:X8} {1,-18} parent=0x{2:X8} ancestor=0x{3:X8} visible={4}",
                    h.ToInt64(), cls, parent.ToInt64(), anc.ToInt64(), IsWindowVisible(h)));
            }
            return true;
        }, IntPtr.Zero);
        foreach (var f in found) Console.WriteLine(f);

        Console.WriteLine();
        Console.WriteLine("=== LumaWall windows (top-level) ===");
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            uint pid;
            GetWindowThreadProcessId(h, out pid);
            if (pid == (uint)lumaPid)
            {
                IntPtr parent = GetParent(h);
                IntPtr anc = GetAncestor(h, 1);
                IntPtr desktop = GetDesktopWindow();
                RECT r;
                GetWindowRect(h, out r);
                Console.WriteLine(string.Format(
                    "  0x{0:X8} cls={1,-20} parent=0x{2:X8} ancestor=0x{3:X8} (desktop=0x{4:X8}) rect={5},{6} {7}x{8} alive={9}",
                    h.ToInt64(), Cls(h), parent.ToInt64(), anc.ToInt64(), desktop.ToInt64(),
                    r.L, r.T, r.R - r.L, r.B - r.T, IsWindow(h)));
            }
            return true;
        }, IntPtr.Zero);

        Console.WriteLine();
        Console.WriteLine("Interpretation:");
        Console.WriteLine("  ancestor == desktop (0x10010)  -> window is NOT attached to a WorkerW");
        Console.WriteLine("  parent   == 0                  -> no owner/parent set");
        return 0;
    }
}
