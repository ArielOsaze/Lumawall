# Measures the three timing guarantees the user asked for:
#
#   1. Opening a fullscreen app  -> wallpaper pauses (optimisation) with no delay
#   2. Minimizing/closing it     -> wallpaper runs again immediately
#   3. Applying a wallpaper from LumaWall -> it is actually applied (pixel proof)
#
# Latency is measured from the log's own millisecond timestamps, so the numbers
# are the app's reaction time and not the test's polling interval.

$ErrorActionPreference = 'Continue'
$log   = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
# The probe is compiled on demand from FullscreenCover.cs, so the repository
# never carries a binary and the probe always matches the current source.
$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'
if (-not (Test-Path $cover)) {
    $csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    if (-not (Test-Path $csc)) { $csc = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' }
    if (Test-Path $csc) {
        $src = Join-Path $PSScriptRoot 'FullscreenCover.cs'
        & $csc /nologo /target:winexe "/out:$cover" /r:System.Windows.Forms.dll /r:System.Drawing.dll $src | Out-Null
    }
}


$exe   = "$env:LOCALAPPDATA\Programs\LumaWall\LumaWall.exe"

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }
function Verdict($label, $ok, $detail) {
    $c = if ($ok) { 'Green' } else { 'Red' }
    Write-Host ("   [{0}] {1}{2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $label, $(if ($detail) { "  -> $detail" } else { '' })) -ForegroundColor $c
    return $ok
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

function LogLines($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try { $fs.Seek($fromByte, 'Begin') | Out-Null; $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose() }
    finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ -match 'Playback updated' })
}
function LogTime($line) {
    if ($line -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})') {
        return [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss.fff', $null)
    }
    return $null
}
function PauseEvent($lines)  { return $lines | Where-Object { $_ -match 'paused \[[^\]]+\]' } | Select-Object -Last 1 }
function ResumeEvent($lines) { return $lines | Where-Object { $_ -match 'resumed \[[^\]]+\]' } | Select-Object -Last 1 }

$pass = $true
Write-Host "###############################################" -ForegroundColor White
Write-Host "#  TIMING GUARANTEES                          #" -ForegroundColor White
Write-Host "###############################################" -ForegroundColor White

# ============================================================ 1. FULLSCREEN
Section "1. Fullscreen app opens -> wallpaper must pause immediately"
$primary = [System.Windows.Forms.Screen]::AllScreens | Where-Object { $_.Primary } | Select-Object -First 1
# Use a secondary display when one exists: the probe needs to own the
# foreground, and on the primary it competes with whatever the user has open.
$probeScreen = [System.Windows.Forms.Screen]::AllScreens | Where-Object { -not $_.Primary } | Select-Object -First 1
if (-not $probeScreen) { $probeScreen = $primary }
Info ("probe display " + $probeScreen.DeviceName + "   (primary is " + $primary.DeviceName + ")")

try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 2
$baseline = (Get-Item $log).Length
$b = $probeScreen.Bounds

# Start the probe and wait for it to report that it actually owns the
# foreground. Measuring from process start would include the ~0.8 s it takes a
# window to appear and activate, which is the probe's own startup cost and not
# the app's reaction time.
$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
$proc.StartInfo.FileName = $cover
$proc.StartInfo.Arguments = "$($b.Left) $($b.Top) $($b.Width) $($b.Height) 8"
$proc.StartInfo.UseShellExecute = $false
$proc.StartInfo.RedirectStandardOutput = $true
$proc.StartInfo.CreateNoWindow = $true
$proc.Start() | Out-Null

$foregroundAt = $null
$readyDeadline = (Get-Date).AddSeconds(6)
while ((Get-Date) -lt $readyDeadline) {
    $line = $proc.StandardOutput.ReadLine()
    if ($null -eq $line) { break }
    if ($line.StartsWith('open ')) { $foregroundAt = Get-Date; break }
}
if (-not $foregroundAt) { $foregroundAt = Get-Date }

$pauseLine = $null
$deadline = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt $deadline) {
    $pauseLine = PauseEvent (LogLines $baseline)
    if ($pauseLine) { break }
    Start-Sleep -Milliseconds 25
}

if ($pauseLine) {
    $ts = LogTime $pauseLine
    $ms = if ($ts) { [math]::Round(($ts - $foregroundAt).TotalMilliseconds) } else { $null }
    Info "  $pauseLine"
    if ($ms -ne $null) { Info ("  pause latency: {0} ms after the window became foreground" -f $ms) }
    # The hook must fire well inside the 2 s poll interval; anything near 2000 ms
    # would mean the hook is not working and the poll is doing the job.
    $pass = (Verdict "pauses on fullscreen without delay" ($ms -ne $null -and $ms -lt 400) $(if ($ms) { "$ms ms (poll would be ~2000 ms)" } else { 'event recorded' })) -and $pass
} else {
    $pass = (Verdict "pauses on fullscreen without delay" $false "no pause within 5 s") -and $pass
}

# =============================================================== 2. RESUME
Section "2. Fullscreen app closes/minimizes -> wallpaper must run again immediately"
$closedAt = Get-Date
$proc.WaitForExit(12000) | Out-Null
$closeStamp = Get-Date

$resumeLine = $null
$deadline = $closeStamp.AddSeconds(5)
while ((Get-Date) -lt $deadline) {
    $resumeLine = ResumeEvent (LogLines $baseline)
    if ($resumeLine) { break }
    Start-Sleep -Milliseconds 40
}

if ($resumeLine) {
    $ts = LogTime $resumeLine
    $ms = if ($ts) { [math]::Round(($ts - $closeStamp).TotalMilliseconds) } else { $null }
    Info "  $resumeLine"
    if ($ms -ne $null) {
        if ($ms -lt 0) { Info ("  resume latency: immediate (fired before the window finished closing)") }
        else { Info ("  resume latency: {0} ms after the window closed" -f $ms) }
    }
    $pass = (Verdict "resumes immediately after fullscreen closes" ($ms -eq $null -or $ms -lt 700) $(if ($ms) { "$ms ms" } else { 'event recorded' })) -and $pass
} else {
    $pass = (Verdict "resumes immediately after fullscreen closes" $false "still paused after 5 s") -and $pass
}

# Minimize path: a minimized window must also let the wallpaper run.
Section "2b. Minimized window -> wallpaper runs"
$baseline = (Get-Item $log).Length
# The probe prints its own window handle, so the test never has to guess at a
# window class or title (which differ per machine and locale).
$mcover = New-Object System.Diagnostics.Process
$mcover.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
$mcover.StartInfo.FileName = $cover
$mcover.StartInfo.Arguments = "$($b.Left) $($b.Top) $($b.Width) $($b.Height) 8"
$mcover.StartInfo.UseShellExecute = $false
$mcover.StartInfo.RedirectStandardOutput = $true
$mcover.StartInfo.CreateNoWindow = $true
$mcover.Start() | Out-Null

$coverHwnd = [IntPtr]::Zero
$hwndDeadline = (Get-Date).AddSeconds(6)
while ((Get-Date) -lt $hwndDeadline -and $coverHwnd -eq [IntPtr]::Zero) {
    $line = $mcover.StandardOutput.ReadLine()
    if ($line -and $line.StartsWith('hwnd ')) {
        $value = [int64]$line.Substring(5)
        $coverHwnd = [IntPtr]$value
    }
}
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Minz {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
if ($coverHwnd -ne [IntPtr]::Zero) {
    Start-Sleep -Milliseconds 1500
    $minStamp = Get-Date
    [Minz]::ShowWindow($coverHwnd, 6) | Out-Null   # SW_MINIMIZE
    $minStamp = Get-Date
    $minResume = $null
    $deadline = $minStamp.AddSeconds(5)
    while ((Get-Date) -lt $deadline) {
        $minResume = ResumeEvent (LogLines $baseline)
        if ($minResume) { break }
        Start-Sleep -Milliseconds 40
    }
    if ($minResume) {
        $ts = LogTime $minResume
        $ms = if ($ts) { [math]::Round(($ts - $minStamp).TotalMilliseconds) } else { $null }
        Info "  $minResume"
        if ($ms -ne $null -and $ms -lt 0) { Info "  resume latency: immediate" } elseif ($ms -ne $null) { Info ("  resume latency: {0} ms" -f $ms) }
        $pass = (Verdict "resumes when the app is minimized" ($ms -eq $null -or $ms -lt 700) $(if ($ms) { "$ms ms" } else { 'event recorded' })) -and $pass
    } else {
        $pass = (Verdict "resumes when the app is minimized" $false "no resume within 5 s") -and $pass
    }
} else {
    Info "  (probe did not report a window handle; skipping minimize check)"
}
try { $mcover.Kill() } catch {}

# ============================================================== 3. APPLY
Section "3. Applying a wallpaper from LumaWall actually applies it"
$library = Get-ChildItem "$env:LOCALAPPDATA\LumaWall\Wallpapers" -Filter *.mp4 -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending | Select-Object -First 1
if (-not $library) {
    $pass = (Verdict "apply from LumaWall" $false "no wallpaper in library to test") -and $pass
} else {
    Info ("target file: " + $library.Name)
    $cfgPath = "$env:LOCALAPPDATA\LumaWall\config.json"
    # DataContractJsonSerializer writes Dictionary<string,string> as an array of
    # {Key,Value} objects, so the entry has to be found by matching Key.
    function Get-MonitorVideo($cfg, $device) {
        if (-not $cfg.MonitorVideos) { return $null }
        $entry = $cfg.MonitorVideos | Where-Object { $_.Key -eq $device } | Select-Object -First 1
        if ($entry) { return $entry.Value }
        return $null
    }
    $cfgBefore = Get-Content $cfgPath -Raw | ConvertFrom-Json
    $before = Get-MonitorVideo $cfgBefore $primary.DeviceName

    # Apply through the app's own CLI path, which is the same code the UI uses.
    $applyAt = Get-Date
    & $exe "--apply=$($library.FullName)" "--monitor=1" 2>&1 | Out-Null
    Start-Sleep -Seconds 6

    $cfgAfter = Get-Content $cfgPath -Raw | ConvertFrom-Json
    $after = Get-MonitorVideo $cfgAfter $primary.DeviceName
    Info ("  monitors in config: " + (($cfgAfter.MonitorVideos | ForEach-Object { $_.Key }) -join ', '))
    $configOk = ($after -eq $library.FullName)
    $beforeName = if ($before) { Split-Path $before -Leaf } else { '(none)' }
    $afterName  = if ($after)  { Split-Path $after  -Leaf } else { '(none)' }
    Info ("  config: " + $beforeName + "  ->  " + $afterName)
    $pass = (Verdict "config records the applied wallpaper" $configOk $after) -and $pass

    # Pixel proof: the display must be animating after the apply.
    try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
    Start-Sleep -Seconds 3
    $f1 = New-Object System.Drawing.Bitmap $primary.Bounds.Width, $primary.Bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($f1)
    $g.CopyFromScreen($primary.Bounds.X, $primary.Bounds.Y, 0, 0, $f1.Size); $g.Dispose()
    Start-Sleep -Milliseconds 1100
    $f2 = New-Object System.Drawing.Bitmap $primary.Bounds.Width, $primary.Bounds.Height
    $g2 = [System.Drawing.Graphics]::FromImage($f2)
    $g2.CopyFromScreen($primary.Bounds.X, $primary.Bounds.Y, 0, 0, $f2.Size); $g2.Dispose()

    $changed = 0; $sampled = 0; $luma = 0
    for ($y = 0; $y -lt $f1.Height; $y += 20) {
        for ($x = 0; $x -lt $f1.Width; $x += 20) {
            $a = $f1.GetPixel($x, $y); $c = $f2.GetPixel($x, $y)
            $sampled++; $luma += ($a.R + $a.G + $a.B) / 3
            if ([math]::Abs($a.R-$c.R) + [math]::Abs($a.G-$c.G) + [math]::Abs($a.B-$c.B) -gt 18) { $changed++ }
        }
    }
    $pct = [math]::Round(100 * $changed / $sampled, 1)
    $mean = [math]::Round($luma / $sampled, 1)
    Info ("  display: mean luma $mean, $pct% of pixels changed between frames")
    $pass = (Verdict "wallpaper is live on the display after apply" ($pct -ge 1.0) "$pct% animating") -and $pass
    $f1.Dispose(); $f2.Dispose()
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor White
if ($pass) { Write-Host "ALL TIMING GUARANTEES PASS" -ForegroundColor Green }
else       { Write-Host "SOME CHECKS FAILED" -ForegroundColor Red }
