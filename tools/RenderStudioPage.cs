// Render the Luma Studio page to a PNG so the layout can be looked at.
//
// Why this exists: every other check on this page is arithmetic - is the key present,
// is the text the right width, does the click throw. None of them can tell whether the
// page looks like something a person would want to use, and that is what was wrong with
// it. This renders the real WPF page, at the real size, to a file.
//
// It builds the page through the app's own MainWindow so it cannot drift from what the
// app draws: the same window, the same fonts, the same theme.

using System;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

internal static class RenderStudioPage
{
    [STAThread]
    private static int Main(string[] args)
    {
        string output = args.Length > 0 ? args[0] : "build/studio-page.png";
        double width = args.Length > 1 ? double.Parse(args[1]) : 1180;
        double height = args.Length > 2 ? double.Parse(args[2]) : 1500;

        var app = new Application();
        app.ShutdownMode = ShutdownMode.OnExplicitShutdown;

        try
        {
            // The app's own assembly, found relative to this executable's own location so
            // it does not depend on the working directory it was launched from.
            string here = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".";
            string exe = null;
            // tools/bin/ -> repository root is two levels up.
            foreach (string candidate in new[]
            {
                Path.GetFullPath(Path.Combine(here, "..", "..", "LumaWall", "bin", "Release", "LumaWall.exe")),
                Path.GetFullPath(Path.Combine(here, "LumaWall", "bin", "Release", "LumaWall.exe")),
                Path.GetFullPath(Path.Combine(here, "..", "LumaWall", "bin", "Release", "LumaWall.exe")),
            })
            {
                if (File.Exists(candidate)) { exe = candidate; break; }
            }
            if (exe == null)
            {
                Console.WriteLine("  cannot find LumaWall.exe near " + here);
                return 1;
            }
            Console.WriteLine("  app: " + exe);

            var assembly = Assembly.LoadFrom(exe);
            Type windowType = assembly.GetType("LumaWall.MainWindow", true);

            // MainWindow's constructor is private in the app (it is a Window subclass with
            // an internal entry point), so it is created through reflection here.
            var window = (Window)Activator.CreateInstance(
                windowType,
                BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public,
                null, null, null);

            window.Width = width;
            window.Height = height;

            // Show it off-screen: a Window has to be shown for WPF to build its visual
            // tree, and a page that was never laid out renders blank.
            window.WindowStartupLocation = WindowStartupLocation.Manual;
            window.Left = -32000;
            window.Top = -32000;
            window.Show();

            // Switch to the page being inspected.
            MethodInfo switchPage = windowType.GetMethod("SwitchPage",
                BindingFlags.Instance | BindingFlags.NonPublic);
            if (switchPage != null) switchPage.Invoke(window, new object[] { "studio" });

            // Let layout and any deferred work finish before the frame is taken.
            for (int i = 0; i < 12; i++)
            {
                window.Dispatcher.Invoke(new Action(delegate { }), DispatcherPriority.ContextIdle);
                System.Threading.Thread.Sleep(60);
            }

            var root = (FrameworkElement)window.Content;
            root.UpdateLayout();

            int pixelWidth = (int)Math.Ceiling(root.ActualWidth);
            int pixelHeight = (int)Math.Ceiling(root.ActualHeight);
            if (pixelWidth <= 0 || pixelHeight <= 0)
            {
                Console.WriteLine("  the window has no size");
                return 1;
            }

            var bitmap = new RenderTargetBitmap(pixelWidth, pixelHeight, 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(root);

            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(bitmap));

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)) ?? ".");
            using (var stream = File.Create(output))
            {
                encoder.Save(stream);
            }

            Console.WriteLine("  wrote " + output + "  (" + pixelWidth + "x" + pixelHeight + ")");
            window.Close();
            app.Shutdown();
            return 0;
        }
        catch (Exception error)
        {
            Console.WriteLine("  FAILED: " + error.GetType().Name + ": " + error.Message);
            Exception inner = error.InnerException;
            while (inner != null)
            {
                Console.WriteLine("    caused by " + inner.GetType().Name + ": " + inner.Message);
                inner = inner.InnerException;
            }
            return 1;
        }
    }
}
