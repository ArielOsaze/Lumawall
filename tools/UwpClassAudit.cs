// UwpClassAudit.cs - finds a reliable way to tell a real UWP app window from a
// shell surface like the Start menu.
//
// The pause detector currently ignores every window whose class is
// Windows.UI.Core.CoreWindow or ApplicationFrameWindow, because the Start menu,
// the input host and similar shell furniture use them. But those classes are
// also used by every real UWP application (games from the Store, Minecraft,
// Roblox, Netflix...), so a fullscreen UWP app never pauses the wallpaper.
//
// Both kinds of window are enumerated here with the properties that could
// distinguish them - process name, window title, styles, size, and the owning
// package - so the filter can be based on evidence instead of a guess.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class UwpClassAudit
{
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] private static extern bool IsZoomed(IntPtr h);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] private static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern int GetPackageFullName(IntPtr hProcess, ref int length, StringBuilder name);

    private delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

    private const int ERROR_INSUFFICIENT_BUFFER = 122;

    private static string Cls(IntPtr h) { var sb = new StringBuilder(160); GetClassName(h, sb, sb.Capacity); return sb.ToString(); }
    private static string Title(IntPtr h) { var sb = new StringBuilder(200); GetWindowText(h, sb, sb.Capacity); return sb.ToString(); }

    private static int Main()
    {
        Console.WriteLine("=== Windows using a UWP-ish window class ===");
        Console.WriteLine();
        Console.WriteLine("  class                     visible zoom title                          process            pkg");
        Console.WriteLine("  ------------------------- ------- ---- ------------------------------ ------------------ ---");

        var rows = new List<string>();
        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            string cls = Cls(h);
            if (cls != "Windows.UI.Core.CoreWindow" && cls != "ApplicationFrameWindow") return true;
            if (!IsWindowVisible(h)) return true;

            uint pid; GetWindowThreadProcessId(h, out pid);
            string procName = "?";
            string pkg = "-";
            try
            {
                var proc = Process.GetProcessById((int)pid);
                procName = proc.ProcessName;
                int len = 0;
                int rc = GetPackageFullName(proc.Handle, ref len, null);
                if (rc == ERROR_INSUFFICIENT_BUFFER && len > 0)
                {
                    var sb = new StringBuilder(len);
                    if (GetPackageFullName(proc.Handle, ref len, sb) == 0)
                    {
                        // Only the family name matters for identification.
                        string full = sb.ToString();
                        int underscore = full.IndexOf('_');
                        pkg = underscore > 0 ? full.Substring(0, underscore) : full;
                    }
                }
            }
            catch { }

            string title = Title(h);
            if (title.Length > 30) title = title.Substring(0, 27) + "...";

            RECT r; GetWindowRect(h, out r);
            int w = r.R - r.L, ht = r.B - r.T;

            rows.Add(string.Format("  {0,-25} {1,-7} {2,-4} {3,-30} {4,-18} {5}",
                cls, "yes", IsZoomed(h) ? "Z" : "-", title, procName, pkg));
            rows.Add(string.Format("      size {0}x{1} at ({2},{3})", w, ht, r.L, r.T));
            return true;
        }, IntPtr.Zero);

        foreach (var row in rows) Console.WriteLine(row);

        Console.WriteLine();
        Console.WriteLine("=== how to tell them apart ===");
        Console.WriteLine("  A shell surface (Start menu, search, input host) has:");
        Console.WriteLine("    - an empty title, and/or");
        Console.WriteLine("    - a process that is not a normal app (ShellExperienceHost,");
        Console.WriteLine("      SearchHost, StartMenuExperienceHost, TextInputHost)");
        Console.WriteLine("  A real UWP app has a title and a normal app process.");
        Console.WriteLine("  The package family name is the strongest signal: shell surfaces");
        Console.WriteLine("  belong to Microsoft.Windows.* / Microsoft.UI.* packages.");
        return 0;
    }
}
