# desktop-shot.ps1 - a full screenshot of the virtual desktop.
#
# Why this exists: "the wallpaper did not apply" can mean three different things and
# they need different fixes - the window is not attached to the desktop, the video
# is not playing, or the wallpaper is playing but something is covering it. The log
# cannot tell them apart, because all three look like a healthy process. A picture
# of the actual desktop can.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/desktop-shot.ps1
#   powershell ... -File tools/desktop-shot.ps1 -Out build/before.png

param([string]$Out = 'build/desktop.png')

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen

$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
$graphics.Dispose()

$dir = Split-Path $Out -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$bitmap.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()

Write-Host ("  saved " + $Out + "  " + $bounds.Width + "x" + $bounds.Height +
            "  (virtual screen origin " + $bounds.Left + "," + $bounds.Top + ")")
