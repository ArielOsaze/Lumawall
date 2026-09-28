# Where does the timer widget live in the window tree?
#
# The widget is parented to the desktop so that it cannot cover an application. That
# makes it a child window, and EnumWindows does not return child windows - which is why
# the display checker could not find it. This prints the desktop host's whole child
# tree with class names and owning processes, so the widget can be identified.
#
# Usage: powershell -File tools/probe-desktop-tree.ps1

Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class D {
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string c, string w);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string w);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rr,B; }
 public static string Cls(IntPtr h) { var sb = new StringBuilder(200); GetClassName(h, sb, 200); return sb.ToString(); }
 public static string Txt(IntPtr h) { var sb = new StringBuilder(200); GetWindowText(h, sb, 200); return sb.ToString(); }
}
'@ -Name D -ErrorAction SilentlyContinue

$luma = (Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $luma) { Write-Output 'LumaWall is not running'; exit 1 }
Write-Output ('LumaWall pid: ' + $luma.Id)

function Show-Tree($parent, $indent) {
    $child = [D]::FindWindowEx($parent, [IntPtr]::Zero, $null, $null)
    while ($child -ne [IntPtr]::Zero) {
        $owner = [uint32]0
        [void][D]::GetWindowThreadProcessId($child, [ref]$owner)
        $r = New-Object D+R
        [void][D]::GetWindowRect($child, [ref]$r)
        $vis = [D]::IsWindowVisible($child)
        $mark = ''
        if ($owner -eq $luma.Id) { $mark = '   <<< LUMAWALL' }
        Write-Output ('{0}{1}  pid={2}  {3}x{4} at {5},{6}  visible={7}{8}' -f `
            $indent, [D]::Cls($child), $owner, ($r.Rr - $r.L), ($r.B - $r.T), $r.L, $r.T, $vis, $mark)
        Show-Tree $child ($indent + '    ')
        $child = [D]::FindWindowEx($parent, $child, $null, $null)
    }
}

foreach ($name in @('Progman', 'WorkerW', 'Shell_TrayWnd')) {
    $h = [D]::FindWindow($name, $null)
    if ($h -eq [IntPtr]::Zero) { Write-Output ("$name : not found"); continue }
    Write-Output ''
    Write-Output ("$name  handle=$h")
    Show-Tree $h '  '
}

# WorkerW is also a class with many instances; enumerate the top level to find them.
Write-Output ''
Write-Output 'top-level WorkerW instances:'
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class E {
 public delegate bool Proc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Proc cb, IntPtr p);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rr,B; }
 public static string Cls(IntPtr h) { var sb = new StringBuilder(200); GetClassName(h, sb, 200); return sb.ToString(); }
}
'@ -Name E -ErrorAction SilentlyContinue

$cb = [E+Proc]{
    param($h, $p)
    if ([E]::Cls($h) -eq 'WorkerW') {
        $r = New-Object E+R
        [void][E]::GetWindowRect($h, [ref]$r)
        Write-Output ('  WorkerW {0}  {1}x{2} at {3},{4}' -f $h, ($r.Rr - $r.L), ($r.B - $r.T), $r.L, $r.T)
    }
    return $true
}
[void][E]::EnumWindows($cb, [IntPtr]::Zero)
