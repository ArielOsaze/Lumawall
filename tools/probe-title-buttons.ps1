# Where are the title-bar buttons, and what are they called?
#
# verify-hover.py moves the pointer to fixed offsets from the window's right edge
# (right-110, right-66, right-22) and assumes those are the three buttons. That worked on
# the primary screen at the default window size, and stopped working once the window was
# moved and resized to fit a smaller test monitor - two of the three offsets missed.
#
# This prints the real rectangles, so the checker can aim at the buttons rather than at
# positions that happen to be right for one window size.
#
# Usage: powershell -File tools/probe-title-buttons.ps1

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class TitleBarProbe {
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out TitleBarRect r);
 [StructLayout(LayoutKind.Sequential)] public struct TitleBarRect { public int L, T, Rr, B; }
}
'@ -ErrorAction SilentlyContinue

$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]

$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }

$r = New-Object TitleBarProbe+TitleBarRect
[void][TitleBarProbe]::GetWindowRect($win.Current.NativeWindowHandle, [ref]$r)
Write-Output ('WINDOW  left={0} top={1} right={2} bottom={3}  {4}x{5}' -f `
    $r.L, $r.T, $r.Rr, $r.B, ($r.Rr - $r.L), ($r.B - $r.T))

$bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
Write-Output ''
Write-Output 'buttons in the title-bar strip (top 60 px of the window):'
foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
    $br = $b.Current.BoundingRectangle
    if ($br.Height -eq 0) { continue }
    if ($br.Y -lt $r.T -or $br.Y -gt ($r.T + 60)) { continue }
    $name = $b.Current.Name
    $aid = ''
    try { $aid = $b.Current.AutomationId } catch { }
    Write-Output ('  x={0,6} y={1,5} w={2,4} h={3,3}  name="{4}"  id="{5}"' -f `
        [int]$br.X, [int]$br.Y, [int]$br.Width, [int]$br.Height, $name, $aid)
}
Write-Output ''
Write-Output ('distance from the window right edge ({0}) to each button centre:' -f $r.Rr)
foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
    $br = $b.Current.BoundingRectangle
    if ($br.Height -eq 0) { continue }
    if ($br.Y -lt $r.T -or $br.Y -gt ($r.T + 60)) { continue }
    $cx = $br.X + $br.Width / 2
    Write-Output ('  right - {0,4:N0}   name="{1}"' -f ($r.Rr - $cx), $b.Current.Name)
}
