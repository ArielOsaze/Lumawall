// FullscreenCover.cs - a borderless window used to prove the per-monitor pause.
//
// Usage:
//   FullscreenCover.exe <left> <top> <width> <height> <seconds>
//
// It opens the window, forces it to the foreground, waits, then closes it.
//
// Windows blocks a background process from stealing the foreground, so a plain
// Activate() is often ignored and the window opens *behind* whatever the user
// is looking at - which made the earlier version of this probe unreliable. The
// AttachThreadInput trick below is the standard way real apps (and games) take
// the foreground: briefly attaching to the current foreground thread's input
// queue lifts the restriction for the duration of the call.

using System;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

internal static class FullscreenCover
{
    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr processId);

    [DllImport("user32.dll")]
    private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern IntPtr SetFocus(IntPtr hWnd);

    private static void ForceForeground(IntPtr hwnd)
    {
        IntPtr foreground = GetForegroundWindow();
        uint targetThread = GetWindowThreadProcessId(hwnd, IntPtr.Zero);
        uint currentThread = GetCurrentThreadId();

        bool attached = false;
        if (foreground != IntPtr.Zero)
        {
            uint foregroundThread = GetWindowThreadProcessId(foreground, IntPtr.Zero);
            if (foregroundThread != 0 && foregroundThread != currentThread)
                attached = AttachThreadInput(currentThread, foregroundThread, true);
        }
        try
        {
            BringWindowToTop(hwnd);
            SetForegroundWindow(hwnd);
            SetFocus(hwnd);
        }
        finally
        {
            if (attached)
            {
                uint foregroundThread = GetWindowThreadProcessId(GetForegroundWindow(), IntPtr.Zero);
                if (foregroundThread != 0 && foregroundThread != currentThread)
                    AttachThreadInput(currentThread, foregroundThread, false);
            }
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length < 5)
        {
            Console.Error.WriteLine("usage: FullscreenCover <left> <top> <w> <h> <seconds>");
            return 2;
        }
        int left = int.Parse(args[0]);
        int top = int.Parse(args[1]);
        int width = int.Parse(args[2]);
        int height = int.Parse(args[3]);
        double seconds = double.Parse(args[4]);

        Application.EnableVisualStyles();
        var form = new Form
        {
            FormBorderStyle = FormBorderStyle.None,
            StartPosition = FormStartPosition.Manual,
            Bounds = new Rectangle(left, top, width, height),
            BackColor = Color.Black,
            ShowInTaskbar = false,
            TopMost = true,
            Text = "LumaWall pause probe"
        };

        form.Shown += delegate
        {
            ForceForeground(form.Handle);
            Console.WriteLine("open " + form.Handle.ToInt64());
            Console.Out.Flush();
        };

        // Print the handle as soon as it exists so a test can target this exact
        // window (to minimize it, for example) without guessing at its title or
        // window class.
        form.HandleCreated += delegate
        {
            Console.WriteLine("hwnd " + form.Handle.ToInt64());
            Console.Out.Flush();
        };

        var timer = new System.Windows.Forms.Timer { Interval = (int)(seconds * 1000) };
        timer.Tick += delegate
        {
            timer.Stop();
            Console.WriteLine("closing");
            Console.Out.Flush();
            form.Close();
        };
        timer.Start();

        Application.Run(form);
        Console.WriteLine("closed");
        Console.Out.Flush();
        return 0;
    }
}
