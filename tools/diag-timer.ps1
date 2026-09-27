# Find the desktop timer window and report exactly where it is and whether it is visible.
#
# The report was "bug timer ada ga muncul" - the timer sometimes does not appear. This
# answers the question with facts instead of a guess: does the window exist, is it
# visible, what rectangle does it occupy, and what is it doing in the z-order.
#
# Usage: powershell -File tools/diag-timer.ps1

Add-Type -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetWindowLong(IntPtr h, int index);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool GetWindowRect(IntPtr h, out RECT r);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool IsWindowVisible(IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern IntPtr GetParent(IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern IntPtr GetAncestor(IntPtr h, uint flags);
public delegate bool EnumProc(IntPtr h, IntPtr p);
[System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
public struct RECT { public int Left, Top, Right, Bottom; }
'@ -Name T -Namespace Diag -ErrorAction SilentlyContinue

function Get-Class([IntPtr]$h) {
    $sb = New-Object System.Text.StringBuilder 256
    [Diag.T]::GetClassName($h, $sb, 256) | Out-Null
    return $sb.ToString()
}

$luma = Get-Process LumaWall -ErrorAction SilentlyContinue
if (-not $luma) { Write-Output '  LumaWall is not running'; exit 1 }
$pids = @($luma | ForEach-Object { $_.Id })
Write-Output ('  LumaWall pids: ' + ($pids -join ', '))

$script:found = @()
$cb = [Diag.T+EnumProc]{
    param([IntPtr]$h, [IntPtr]$p)
    $pp = 0
    [Diag.T]::GetWindowThreadProcessId($h, [ref]$pp) | Out-Null
    if ($pids -notcontains $pp) { return $true }
    $r = New-Object Diag.T+RECT
    [Diag.T]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left
    $ht = $r.Bottom - $r.Top
    $cls = Get-Class $h
    $vis = [Diag.T]::IsWindowVisible($h)
    $ex = [Diag.T]::GetWindowLong($h, -20)
    $style = [Diag.T]::GetWindowLong($h, -16)
    $parent = [Diag.T]::GetParent($h)
    $root = [Diag.T]::GetAncestor($h, 2)
    $script:found += [pscustomobject]@{
        H = $h; Class = $cls; Visible = $vis; W = $w; Ht = $ht
        X = $r.Left; Y = $r.Top; Ex = $ex; Style = $style
        Parent = $parent; Root = $root
    }
    return $true
}
[Diag.T]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

Write-Output ''
Write-Output '  every top-level window owned by LumaWall:'
foreach ($f in $script:found) {
    Write-Output ('    class={0}' -f $f.Class)
    Write-Output ('      visible={0}  {1}x{2} at {3},{4}' -f $f.Visible, $f.W, $f.Ht, $f.X, $f.Y)
    Write-Output ('      exStyle=0x{0:X}  style=0x{1:X}' -f $f.Ex, $f.Style)
    Write-Output ('      parent={0}  root={1}' -f $f.Parent, $f.Root)
    $wsExVisible = 0x10000000
    $wsVisible = 0x10000000
    $topmost = ($f.Ex -band 0x8) -ne 0
    $layered = ($f.Ex -band 0x80000) -ne 0
    $child = ($f.Style -band 0x40000000) -ne 0
    Write-Output ('      topmost={0} layered={1} child={2}' -f $topmost, $layered, $child)
}

# The timer is the small one. Report a verdict on it specifically.
$timer = $script:found | Where-Object { $_.W -gt 40 -and $_.W -lt 900 -and $_.Ht -gt 30 -and $_.Ht -lt 500 } |
         Select-Object -First 1
Write-Output ''
if (-not $timer) {
    Write-Output '  FAIL no small LumaWall window exists - the timer was never created'
    Write-Output '       (a timer that is switched on but has no window is the reported bug)'
    exit 1
}

Write-Output ('  timer window: {0}x{1} at {2},{3}' -f $timer.W, $timer.Ht, $timer.X, $timer.Y)
if (-not $timer.Visible) {
    Write-Output '  FAIL the timer window exists but is NOT visible'
    exit 1
}
Write-Output '  PASS the timer window exists and is visible'
exit 0
