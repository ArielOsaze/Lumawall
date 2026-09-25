param(
  [string]$ExePath = 'C:\Users\ariel\AppData\Local\Programs\LumaWall\LumaWall.exe',
  [int]$SampleSeconds = 12
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public static class LwFlicker
{
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    public static string Run(int seconds)
    {
        try { SetProcessDPIAware(); } catch {}
        var screens = Screen.AllScreens;
        int n = screens.Length;
        double[] minLuma = new double[n];
        int[] black = new int[n];
        int[] frames = new int[n];
        for (int i = 0; i < n; i++) minLuma[i] = 999;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        while (sw.Elapsed.TotalSeconds < seconds)
        {
            for (int i = 0; i < n; i++)
            {
                var b = screens[i].Bounds;
                if (b.Width <= 0 || b.Height <= 0) continue;
                using (var full = new Bitmap(b.Width, b.Height, PixelFormat.Format32bppArgb))
                {
                    using (var g = Graphics.FromImage(full))
                        g.CopyFromScreen(b.Left, b.Top, 0, 0, full.Size, CopyPixelOperation.SourceCopy);
                    double luma = AverageLuma(full);
                    frames[i]++;
                    if (luma < minLuma[i]) minLuma[i] = luma;
                    if (luma < 4) black[i]++;
                }
            }
        }
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < n; i++)
            sb.AppendLine(string.Format("{0}: frames={1} nearBlack={2} minLuma={3:F2}", screens[i].DeviceName, frames[i], black[i], minLuma[i]));
        return sb.ToString();
    }

    static double AverageLuma(Bitmap bmp)
    {
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            int stride = data.Stride, w = bmp.Width, h = bmp.Height;
            byte[] row = new byte[w * 4];
            long sum = 0, count = 0;
            for (int y = 0; y < h; y += 6)
            {
                Marshal.Copy(data.Scan0 + y * stride, row, 0, w * 4);
                for (int x = 0; x < w; x += 6)
                {
                    int o = x * 4;
                    sum += (row[o] + row[o + 1] + row[o + 2]) / 3;
                    count++;
                }
            }
            return count == 0 ? 0 : (double)sum / count;
        }
        finally { bmp.UnlockBits(data); }
    }
}
'@

$configPath = Join-Path $env:LOCALAPPDATA 'LumaWall\config.json'
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$primary = [System.Windows.Forms.Screen]::PrimaryScreen
$pair = @($config.MonitorVideos | Where-Object Key -eq $primary.DeviceName)[0]
$original = [string]$pair.Value
$assets = Join-Path (Split-Path $ExePath) 'assets'
$alternate = Join-Path $assets 'amber-orbit.mp4'
if (-not (Test-Path -LiteralPath $alternate)) { throw "alternate asset missing: $alternate" }
if ($original -eq $alternate) { $alternate = Join-Path $assets 'aqua-nova.mp4' }

Write-Output ("original primary video: " + $original)
Write-Output ("alternate video       : " + $alternate)
Write-Output "Minimizing all windows for the measurement..."

$job = Start-Job -ScriptBlock {
  param($code, $secs)
  Add-Type -AssemblyName System.Drawing
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing, System.Windows.Forms
  [LwFlicker]::Run($secs)
} -ArgumentList $code, $SampleSeconds

$shell = New-Object -ComObject Shell.Application
$shell.MinimizeAll()
Start-Sleep -Milliseconds 1200

Write-Output "Applying alternate wallpaper (transition test)..."
Start-Process -FilePath $ExePath -ArgumentList ('--apply="' + $alternate + '"'), '--silent' | Out-Null

Wait-Job $job | Out-Null
$result = Receive-Job $job
Remove-Job $job -Force

Write-Output "Restoring original wallpaper..."
Start-Process -FilePath $ExePath -ArgumentList ('--apply="' + $original + '"'), '--silent' | Out-Null
Start-Sleep -Seconds 3
$shell.UndoMinimizeAll()

Write-Output "=== FLICKER RESULT (nearBlack > 0 means a black frame appeared) ==="
Write-Output $result
