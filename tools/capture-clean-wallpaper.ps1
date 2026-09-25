# Captures a CLEAN wallpaper image - just the animation, no desktop icons, no
# taskbar, no other application windows.
#
# The old capture (desktop-live.png) was made with CopyFromScreen over the live
# desktop, so it contained the user's desktop icons, the taskbar, and windows
# from other programs. That is unusable as marketing material.
#
# This script records a wallpaper window itself. The wallpaper windows are owned
# by LumaWall and parented to the desktop, so they cannot be captured with a
# screen grab without also grabbing whatever is on top. Instead this renders a
# frame directly from the source video file with ffmpeg, which is exactly what
# the wallpaper engine displays - pixel for pixel, with nothing else.

param(
    [string]$Source,
    [string]$Out,
    [double]$At = 3.0,
    [int]$Width = 1920,
    [int]$Height = 1080
)

$ErrorActionPreference = 'Stop'

function Info($t) { Write-Host "   $t" }

if (-not $Source) {
    # Default: the first wallpaper in the library, so the script works with no
    # arguments on a fresh clone.
    $lib = Join-Path $env:LOCALAPPDATA 'LumaWall\Wallpapers'
    $Source = (Get-ChildItem $lib -Filter *.mp4 -File | Select-Object -First 1).FullName
}
if (-not $Out) { $Out = Join-Path (Split-Path -Parent $PSScriptRoot) 'site\assets\shots\wallpaper-clean.png' }

if (-not (Test-Path $Source)) { throw "source not found: $Source" }

$ffmpeg = 'ffmpeg'
$probe = & ffprobe -v error -select_streams v:0 `
    -show_entries stream=width,height,duration,nb_frames `
    -of default=noprint_wrappers=1 $Source 2>&1
Write-Host "Source: $(Split-Path -Leaf $Source)"
$probe | ForEach-Object { Info $_ }

# Grab the frame. -ss before -i seeks fast and accurately on the input.
& $ffmpeg -v error -ss $At -i $Source -frames:v 1 -y `
    -vf "scale=${Width}:${Height}:force_original_aspect_ratio=increase,crop=${Width}:${Height}" `
    $Out

if (-not (Test-Path $Out)) { throw "ffmpeg produced no output" }

$bytes = (Get-Item $Out).Length
Info "written: $Out ($([math]::Round($bytes/1KB)) KB)"
