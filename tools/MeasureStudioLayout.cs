// Measure the two columns of the Luma Studio page, so a layout imbalance is a number
// rather than an impression.
//
// Why: a vision check said the left column ends well above the right one, leaving an
// awkward gap. That is a claim about heights, and heights can be measured. The two
// columns are found by walking the visual tree for the Grid that BuildStudio creates,
// which is the only Grid on the page with exactly two columns of these widths.

using System;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

internal static class MeasureStudioLayout
{
    [STAThread]
    private static int Main(string[] args)
    {
        var app = new Application();
        app.ShutdownMode = ShutdownMode.OnExplicitShutdown;

        try
        {
            string here = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".";
            string exe = null;
            foreach (string candidate in new[]
            {
                Path.GetFullPath(Path.Combine(here, "..", "..", "LumaWall", "bin", "Release", "LumaWall.exe")),
                Path.GetFullPath(Path.Combine(here, "..", "LumaWall", "bin", "Release", "LumaWall.exe")),
                Path.GetFullPath(Path.Combine(here, "LumaWall", "bin", "Release", "LumaWall.exe")),
            })
            {
                if (File.Exists(candidate)) { exe = candidate; break; }
            }
            if (exe == null) { Console.WriteLine("  cannot find LumaWall.exe"); return 1; }

            var assembly = Assembly.LoadFrom(exe);
            Type windowType = assembly.GetType("LumaWall.MainWindow", true);
            var window = (Window)Activator.CreateInstance(
                windowType,
                BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public,
                null, null, null);

            window.Width = 1180;
            window.Height = 1150;
            window.WindowStartupLocation = WindowStartupLocation.Manual;
            window.Left = -32000;
            window.Top = -32000;
            window.Show();

            MethodInfo switchPage = windowType.GetMethod("SwitchPage",
                BindingFlags.Instance | BindingFlags.NonPublic);
            if (switchPage != null) switchPage.Invoke(window, new object[] { "studio" });

            for (int i = 0; i < 14; i++)
            {
                window.Dispatcher.Invoke(new Action(delegate { }), DispatcherPriority.ContextIdle);
                System.Threading.Thread.Sleep(60);
            }

            var root = (FrameworkElement)window.Content;
            root.UpdateLayout();

            // The two-column Grid: the one whose first column is a fixed 330.
            Grid columns = null;
            Walk(root, delegate(DependencyObject node)
            {
                var grid = node as Grid;
                if (grid == null || grid.ColumnDefinitions.Count != 2) return;
                if (Math.Abs(grid.ColumnDefinitions[0].Width.Value - 330) < 0.5) columns = grid;
            });

            if (columns == null) { Console.WriteLine("  the two-column grid was not found"); return 1; }

            var left = columns.Children[0] as FrameworkElement;
            var right = columns.Children[1] as FrameworkElement;

            Console.WriteLine("  window content   : {0:0} x {1:0}", root.ActualWidth, root.ActualHeight);

            // A Grid stretches both columns to the same height, so ActualHeight is always
            // equal and says nothing about balance. The number that matters is the sum of
            // the cards in each column - that is where the content actually ends.
            double leftContent = ContentHeight(left);
            double rightContent = ContentHeight(right);
            Console.WriteLine("  left content     : {0:0} px of cards", leftContent);
            Console.WriteLine("  right content    : {0:0} px of cards", rightContent);

            double gap = Math.Abs(rightContent - leftContent);
            bool balanced = gap <= 220;
            Console.WriteLine("  difference       : {0:0} px {1}", gap,
                balanced ? "(acceptable)" : "(LARGE - the short column will read as unfinished)");

            Console.WriteLine();
            Console.WriteLine("  left column cards:");
            Describe(left);
            Console.WriteLine("  right column cards:");
            Describe(right);

            // The verdict is written to a file as well as printed, because the process exit
            // code cannot be relied on here: this is a WPF app, and a WPF Application that
            // has shown a Window does not always hand its exit code back to the shell. The
            // first version of this tool returned 1 for an out-of-balance page and the
            // caller saw 127 - "command not found" - from a run that had succeeded.
            //
            // A file is unambiguous: the checker reads it or it is missing, and either way
            // the answer is the tool's own, not the shell's.
            string resultPath = args.Length > 0 ? args[0] : "build/studio-layout.json";
            var report = new System.Text.StringBuilder();
            report.Append("{\n");
            report.AppendFormat("  \"leftContent\": {0:0},\n", leftContent);
            report.AppendFormat("  \"rightContent\": {0:0},\n", rightContent);
            report.AppendFormat("  \"difference\": {0:0},\n", gap);
            report.AppendFormat("  \"limit\": 220,\n");
            report.AppendFormat("  \"balanced\": {0}\n", balanced ? "true" : "false");
            report.Append("}\n");

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(resultPath)) ?? ".");
            File.WriteAllText(resultPath, report.ToString());
            Console.WriteLine();
            Console.WriteLine("  wrote " + resultPath);

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

    /// <summary>The total height of a column's children, which is where its content ends.</summary>
    private static double ContentHeight(FrameworkElement column)
    {
        if (!(column is Panel)) return 0;
        double total = 0;
        foreach (UIElement child in ((Panel)column).Children)
        {
            var element = child as FrameworkElement;
            if (element == null) continue;
            total += element.ActualHeight + element.Margin.Top + element.Margin.Bottom;
        }
        return total;
    }

    private static void Describe(FrameworkElement column)
    {
        if (!(column is Panel)) return;
        foreach (UIElement child in ((Panel)column).Children)
        {
            var element = child as FrameworkElement;
            if (element == null) continue;

            string title = TitleOf(element);
            Console.WriteLine("    {0,7:0} px  {1}", element.ActualHeight, title);
        }
    }

    /// <summary>The first TextBlock in a card is its heading.</summary>
    private static string TitleOf(DependencyObject node)
    {
        string found = null;
        Walk(node, delegate(DependencyObject child)
        {
            if (found != null) return;
            var text = child as TextBlock;
            if (text != null && !string.IsNullOrEmpty(text.Text) && text.FontSize >= 13)
                found = text.Text;
        });
        return found ?? "(no heading)";
    }

    private static void Walk(DependencyObject node, Action<DependencyObject> visit)
    {
        if (node == null) return;
        visit(node);
        int count = VisualTreeHelper.GetChildrenCount(node);
        for (int i = 0; i < count; i++)
        {
            Walk(VisualTreeHelper.GetChild(node, i), visit);
        }
    }
}
