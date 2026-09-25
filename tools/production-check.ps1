# Full production acceptance run: every behavioural guarantee in one pass.
#
# Each check maps to something a user can actually notice, so a green run means
# the app is safe to publish rather than merely "it compiles".

$ErrorActionPreference = 'Continue'
$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
$results = @()

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Record($name, $ok, $detail) {
    $script:results += [pscustomobject]@{ Check = $name; Result = $(if ($ok) { 'PASS' } else { 'FAIL' }); Detail = $detail }
    $colour = if ($ok) { 'Green' } else { 'Red' }
    Write-Host ("   [{0}] {1}{2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $name, $(if ($detail) { "  -> $detail" } else { '' })) -ForegroundColor $colour
}
function Read-New($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try { $fs.Seek($fromByte, 'Begin') | Out-Null; $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose() }
    finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ })
}

# The log survives restarts and is appended to, so it still holds the failures
# of earlier builds. Only the current process's lines describe the build under
# test.
$script:currentPid = (Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1).Id
function Read-Current {
    if (-not (Test-Path $log)) { return @() }
    return @(Get-Content $log | Where-Object { $_ -match ("\[" + $script:currentPid + "\]") })
}

Write-Host "###############################################" -ForegroundColor White
Write-Host "#  LumaWall - PRODUCTION ACCEPTANCE RUN       #" -ForegroundColor White
Write-Host "###############################################" -ForegroundColor White

# ---------------------------------------------------------------- 1. process
Section "1. Process health"
$p = Get-Process LumaWall -ErrorAction SilentlyContinue
Record "app is running" ([bool]$p) $(if ($p) { "pid $($p.Id)" } else { "" })
if (-not $p) { Write-Host "`nAborting: app must be running." -ForegroundColor Red; exit 1 }
Record "single instance only" ((Get-Process LumaWall -ErrorAction SilentlyContinue).Count -eq 1) ""

# ------------------------------------------------------------ 2. render
Section "2. Wallpapers are actually animating (pixel proof)"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'render-check.ps1') *> $null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Dz2 {
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
$defView = [Dz2]::FindWindowEx([Dz2]::FindWindow('Progman', $null), [IntPtr]::Zero, 'SHELLDLL_DefView', $null)
$listView = [Dz2]::FindWindowEx($defView, [IntPtr]::Zero, 'SysListView32', $null)
if ($listView -ne [IntPtr]::Zero) { [Dz2]::ShowWindow($listView, 0) | Out-Null }
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3

foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
    $bmp1 = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp1)
    $g.CopyFromScreen($s.Bounds.X, $s.Bounds.Y, 0, 0, $bmp1.Size); $g.Dispose()
    Start-Sleep -Milliseconds 1100
    $bmp2 = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height
    $g2 = [System.Drawing.Graphics]::FromImage($bmp2)
    $g2.CopyFromScreen($s.Bounds.X, $s.Bounds.Y, 0, 0, $bmp2.Size); $g2.Dispose()

    $changed = 0; $sampled = 0; $luma = 0
    for ($y = 0; $y -lt $bmp1.Height; $y += 24) {
        for ($x = 0; $x -lt $bmp1.Width; $x += 24) {
            $a = $bmp1.GetPixel($x, $y); $b = $bmp2.GetPixel($x, $y)
            $sampled++
            $luma += ($a.R + $a.G + $a.B) / 3
            if ([math]::Abs($a.R-$b.R) + [math]::Abs($a.G-$b.G) + [math]::Abs($a.B-$b.B) -gt 18) { $changed++ }
        }
    }
    $pct = [math]::Round(100 * $changed / $sampled, 1)
    $mean = [math]::Round($luma / $sampled, 1)
    Record ($s.DeviceName + " animating") ($pct -ge 1.0) ("luma $mean, changed $pct%")
    $bmp1.Dispose(); $bmp2.Dispose()
}

# ------------------------------------------------------- 3. per-monitor pause
Section "3. Per-monitor pause (fullscreen on one display only)"
# Clear the stage so no unrelated maximized window is covering a display.
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3
$baseline = (Get-Item $log).Length
$game = [System.Windows.Forms.Screen]::AllScreens | Where-Object { -not $_.Primary } | Select-Object -First 1
if ($game) {
    $b = $game.Bounds
    $cover = Start-Process -FilePath (Join-Path $PSScriptRoot 'FullscreenCover.exe') `
        -ArgumentList $b.Left, $b.Top, $b.Width, $b.Height, '6' -PassThru
    Start-Sleep -Milliseconds 2000
    $lines = Read-New $baseline
    $pauseLine = $lines | Where-Object { $_ -match 'paused \[' } | Select-Object -Last 1
    $otherPaused = $false
    if ($pauseLine -match 'paused \[([^\]]*)\]') { $otherPaused = $Matches[1] -match 'DISPLAY1' -and $game.DeviceName -ne '\.\DISPLAY1' }
    Record "covered display paused" ([bool]$pauseLine) $(if ($pauseLine) { ($pauseLine -split 'Playback updated')[1] } else { '' })
    Record "other displays still running" (-not $otherPaused) $(if ($otherPaused) { 'a non-covered display was paused' } else { 'correct' })

    $t0 = Get-Date
    $cover.WaitForExit(12000) | Out-Null
    $closedAt = Get-Date
    $resume = $null
    while ((Get-Date) -lt $closedAt.AddSeconds(8)) {
        $resume = (Read-New $baseline) | Where-Object { $_ -match 'resumed \[[^\]]*DISPLAY' } | Select-Object -Last 1
        if ($resume) { break }
        Start-Sleep -Milliseconds 80
    }
    Record "instant resume after close" ([bool]$resume) $(if ($resume) { 'hook fired' } else { 'still paused' })
} else {
    Record "per-monitor pause" $false "needs 2+ displays"
}

# --------------------------------------------------- 4. no crash / no errors
Section "4. Runtime cleanliness"
$current = Read-Current
$errors = $current | Select-String -Pattern 'UNHANDLED|FATAL|UNOBSERVED' -CaseSensitive:$false
Record "no unhandled exceptions" (-not $errors) $(if ($errors) { "$($errors.Count) found" } else { "clean (pid $script:currentPid)" })
$spam = $current | Select-String -Pattern 'lost its desktop host, re-attaching' -CaseSensitive:$false
Record "no attach spam" (-not $spam) $(if ($spam) { "$($spam.Count) lines" } else { 'health ticks are quiet' })

# ------------------------------------------------------------ 5. resources
Section "5. Resource stability"
$before = (Get-Process LumaWall).WorkingSet64
$h1 = (Get-Process LumaWall).HandleCount
Start-Sleep -Seconds 12
$after = (Get-Process LumaWall).WorkingSet64
$h2 = (Get-Process LumaWall).HandleCount
$deltaMb = [math]::Round(($after - $before) / 1MB, 1)
Record "memory stable" ($deltaMb -lt 12) ("$deltaMb MB over 12 s")
Record "handles stable" ([math]::Abs($h2 - $h1) -lt 60) ("$($h2 - $h1) change")

# ------------------------------------------------------------------ summary
Write-Host ""
Write-Host "===============================================" -ForegroundColor White
$results | Format-Table -AutoSize | Out-String | Write-Host
$failed = ($results | Where-Object { $_.Result -eq 'FAIL' }).Count
$total = $results.Count
Write-Host ("$($total - $failed)/$total checks passed") -ForegroundColor $(if ($failed -eq 0) { 'Green' } else { 'Red' })
if ($failed -eq 0) { Write-Host "PRODUCTION READY" -ForegroundColor Green } else { Write-Host "$failed CHECK(S) FAILED" -ForegroundColor Red }
exit $failed
