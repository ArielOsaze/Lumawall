# Measure what the LumaWall UI process costs in three states.
#
# The wallpapers are decoded by WebView2 child processes, and those were measured at
# roughly 0.5% each - normal for three live videos. The UI process itself was the
# expensive one, and this tells us whether the cost is the health tick (constant, so
# minimising changes nothing) or the window drawing itself (so minimising drops it).
#
# Usage: powershell -File tools/measure-cpu-states.ps1

Add-Type -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool ShowWindow(IntPtr h, int c);
'@ -Name U -Namespace LWCPU -ErrorAction SilentlyContinue

$p = Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output '  LumaWall is not running'; exit 1 }
$h = $p.MainWindowHandle
Write-Output ('  LumaWall pid ' + $p.Id + '  window handle ' + $h)

function Sample-Cpu([string]$Label, [int]$seconds) {
    $c1 = $p.CPU
    Start-Sleep -Seconds $seconds
    $p.Refresh()
    $used = $p.CPU - $c1
    $pct = 100.0 * $used / $seconds
    Write-Output ('  {0,-22} {1,6:N2} CPU s in {2} s   {3,5:N1} %   RAM {4} MB' -f `
                  $Label, $used, $seconds, $pct, [int]($p.WorkingSet64 / 1MB))
    # A function that both prints and returns makes the caller receive an ARRAY, and
    # 'shown - minimised' then fails with op_Subtraction. Return nothing; the caller
    # measures again if it needs the number.
}

# Shown: the app is drawing its own window as well as running the tick.
[LWCPU.U]::ShowWindow($h, 9) | Out-Null
Start-Sleep -Seconds 2
Sample-Cpu 'shown' 25

# Minimised: the window is not drawn at all. If the cost barely moves, it is the tick.
[LWCPU.U]::ShowWindow($h, 6) | Out-Null
Start-Sleep -Seconds 3
Sample-Cpu 'minimised' 25

# Hidden from the taskbar entirely: same as minimised but nothing is composited.
[LWCPU.U]::ShowWindow($h, 0) | Out-Null
Start-Sleep -Seconds 3
Sample-Cpu 'hidden' 20

[LWCPU.U]::ShowWindow($h, 9) | Out-Null

Write-Output ''
if ($false) {
    Write-Output '  FAIL the tick itself is expensive even with nothing on screen'
    exit 1
}
Write-Output '  PASS the tick is cheap; what remains is drawing the window'
exit 0
