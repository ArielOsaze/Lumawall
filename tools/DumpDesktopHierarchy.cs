// DumpDesktopHierarchy.cs - prints the real desktop window hierarchy so the
// host-finding logic can be based on facts instead of the classic
// (and apparently outdated) "WorkerW after SHELLDLL_DefView" assumption.
//
// The app re-attached in a loop after an Explorer restart, which means
// FindDesktopHost() returned nothing usable and AttachToWallpaper fell back to
// Progman. This shows where SHELLDLL_DefView actually lives and which WorkerW
// is the right wallpaper host on this Windows build.

using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

internal static class DumpDesktopHierarchy
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr h);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr h, uint f);
    [DllImport("user32.dll")] private static extern IntPtr FindWindow(string c, string t);
    [DllImport("user32.dll")] private static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);

    private delegate bool EnumProc(IntPtr h, IntPtr p);

    private static string Cls(IntPtr h)
    {
        var sb = new StringBuilder(160);
        GetClassName(h, sb, sb.Capacity);
        return sb.ToString();
    }

    private static string Describe(IntPtr h, string indent)
    {
        long ex = GetWindowLongPtr64(h, -20).ToInt64();
        return string.Format("{0}0x{1:X8} {2,-22} visible={3,-5} parent=0x{4:X8} ex=0x{5:X}",
            indent, h.ToInt64(), Cls(h), IsWindowVisible(h), GetParent(h).ToInt64(), ex);
    }

    private static int Main()
    {
        Console.WriteLine("=== Progman ===");
        IntPtr progman = FindWindow("Progman", null);
        Console.WriteLine(Describe(progman, "  "));
        long progmanEx = GetWindowLongPtr64(progman, -20).ToInt64();
        bool raised = (progmanEx & 0x00200000L) != 0;
        Console.WriteLine("  WS_EX_NOREDIRECTIONBITMAP (raised desktop) = " + raised);

        Console.WriteLine();
        Console.WriteLine("=== children of Progman ===");
        EnumChildWindows(progman, delegate(IntPtr h, IntPtr p)
        {
            Console.WriteLine(Describe(h, "  "));
            return true;
        }, IntPtr.Zero);

        Console.WriteLine();
        Console.WriteLine("=== top-level windows: Progman, WorkerW, SHELLDLL_DefView ===");
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            string c = Cls(h);
            if (c == "Progman" || c == "WorkerW" || c == "SHELLDLL_DefView")
                Console.WriteLine(Describe(h, "  "));
            return true;
        }, IntPtr.Zero);

        Console.WriteLine();
        Console.WriteLine("=== which top-level window CONTAINS SHELLDLL_DefView? ===");
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            IntPtr defView = FindWindowEx(h, IntPtr.Zero, "SHELLDLL_DefView", null);
            if (defView != IntPtr.Zero)
            {
                Console.WriteLine("  icons live in: " + Describe(h, ""));
                Console.WriteLine("    child: " + Describe(defView, ""));
            }
            return true;
        }, IntPtr.Zero);

        Console.WriteLine();
        Console.WriteLine("=== candidate wallpaper hosts ===");
        IntPtr w1 = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
        Console.WriteLine("  FindWindowEx(Progman, WorkerW)      = 0x" + w1.ToInt64().ToString("X") + (w1 != IntPtr.Zero ? "  " + Cls(w1) : "  (none)"));
        IntPtr iconsWnd = IntPtr.Zero;
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            if (FindWindowEx(h, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero) { iconsWnd = h; return false; }
            return true;
        }, IntPtr.Zero);
        IntPtr w2 = FindWindowEx(IntPtr.Zero, iconsWnd, "WorkerW", null);
        Console.WriteLine("  FindWindowEx(after icons, WorkerW)  = 0x" + w2.ToInt64().ToString("X") + (w2 != IntPtr.Zero ? "  " + Cls(w2) : "  (none)"));

        Console.WriteLine();
        Console.WriteLine("=== does Progman directly contain the wallpaper WorkerW? ===");
        IntPtr ww = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
        if (ww != IntPtr.Zero)
        {
            Console.WriteLine("  yes - WorkerW 0x" + ww.ToInt64().ToString("X") + " is a child of Progman");
            Console.WriteLine("  its children:");
            EnumChildWindows(ww, delegate(IntPtr h, IntPtr p) { Console.WriteLine(Describe(h, "    ")); return true; }, IntPtr.Zero);
        }
        else
        {
            Console.WriteLine("  no WorkerW child of Progman");
        }
        return 0;
    }
}
