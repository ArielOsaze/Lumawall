# show-desktop.ps1 - reveals the desktop so a screenshot shows the wallpapers.
#
# Why this exists:
#
# A wallpaper bug is invisible while application windows cover the screens, and on
# this machine every monitor is covered most of the time. A screenshot taken then
# shows the apps, not the wallpapers, and "the wallpaper is not applied" cannot be
# told apart from "the wallpaper is applied and hidden".
#
# This sends Win+D, waits, screenshots, and sends Win+D again to restore the
# windows exactly as they were. Nothing is closed and nothing is moved.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/show-desktop.ps1 -Out build/desktop.png

param(
    [string]$Out = 'build/desktop-visible.png',
    [int]$SettleMs = 1200
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Keys {
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    public const byte VK_LWIN = 0x5B;
    public const byte VK_D = 0x44;
    public const uint KEYEVENTF_KEYUP = 0x0002;

    public static void ShowDesktop() {
        keybd_event(VK_LWIN, 0, 0, UIntPtr.Zero);
        keybd_event(VK_D, 0, 0, UIntPtr.Zero);
        System.Threading.Thread.Sleep(60);
        keybd_event(VK_D, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
    }
}
'@

function Save-Shot {
    param([string]$Path)
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
    $graphics.Dispose()
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    Write-Host ("  saved " + $Path)
}

Write-Host '  showing the desktop ...'
[Keys]::ShowDesktop()
Start-Sleep -Milliseconds $SettleMs
Save-Shot -Path $Out

Write-Host '  restoring the windows ...'
[Keys]::ShowDesktop()
Start-Sleep -Milliseconds 400
Write-Host '  done'
