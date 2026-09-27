# Prove the Luma Studio placement bug is gone.
#
# The complaint was: "bug tiap pilih palcement yg berbeda langsung di scroll keatas
# sama systemnya" - choosing a different placement threw the page back to the top.
#
# The placement pad is a 3x3 grid of Borders, not Buttons, so UI Automation cannot
# invoke it. This drives it the way a user does: open Luma Studio, scroll down, click a
# cell of the pad with the mouse, and read the page scroll offset before and after. It
# fails if the offset collapses towards the top, which is the bug.
#
# The window is moved on-screen first: it is remembered at its last position, which can
# be off-screen, and a mouse click at negative coordinates goes nowhere.
#
# Usage: powershell -File tools/test-studio-scroll.ps1

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

Add-Type -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern void mouse_event(uint f, uint dx, uint dy, uint d, int e);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetForegroundWindow(IntPtr h);
'@ -Name Native -Namespace LW -ErrorAction SilentlyContinue

$auto  = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl  = [System.Windows.Automation.ControlType]

$root = $auto::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')
$win = $root.FindFirst($scope::Children, $cond)
if (-not $win) { Write-Output '  FAIL the LumaWall window was not found'; exit 1 }

function Get-Buttons {
    $bcond = New-Object System.Windows.Automation.PropertyCondition(
        $auto::ControlTypeProperty, $ctrl::Button)
    return $win.FindAll($scope::Descendants, $bcond)
}

function Click-Button([string]$Label) {
    foreach ($b in (Get-Buttons)) {
        if ($b.Current.Name -eq $Label) {
            $p = $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            $p.Invoke()
            return $true
        }
    }
    return $false
}

function Get-Scroller {
    $scond = New-Object System.Windows.Automation.PropertyCondition(
        $auto::IsScrollPatternAvailableProperty, $true)
    $panes = $win.FindAll($scope::Descendants, $scond)
    $best = $null
    foreach ($p in $panes) {
        $sp = $p.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
        if ($sp.Current.VerticallyScrollable) {
            $r = $p.Current.BoundingRectangle
            if (-not $best -or $r.Height -gt $best.Height) {
                $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height }
            }
        }
    }
    return $best
}

# Every Text element, so the placement name can be found wherever it is on the page.
function Get-Texts {
    $tcond = New-Object System.Windows.Automation.PropertyCondition(
        $auto::ControlTypeProperty, $ctrl::Text)
    return $win.FindAll($scope::Descendants, $tcond)
}

$POS_WORDS = @(
    'Kiri atas','Atas tengah','Kanan atas','Kiri tengah','Tengah','Kanan tengah','Kiri bawah','Bawah tengah','Kanan bawah',
    'Top left','Top centre','Top right','Middle left','Centre','Middle right','Bottom left','Bottom centre','Bottom right',
    'Top center','Middle center','Bottom center')

function Get-PositionLabel {
    foreach ($e in (Get-Texts)) {
        $n = $e.Current.Name
        if ($n -and ($POS_WORDS -contains $n.Trim())) {
            $r = $e.Current.BoundingRectangle
            if ($r.Width -gt 20 -and $r.Height -gt 8) {
                return [pscustomobject]@{ Name = $n.Trim(); Left = [int]$r.Left; Top = [int]$r.Top;
                                          Width = [int]$r.Width; Height = [int]$r.Height }
            }
        }
    }
    return $null
}

function Click-At([int]$x, [int]$y) {
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($x, $y)
    Start-Sleep -Milliseconds 220
    [LW.Native]::mouse_event(0x0002, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 60
    [LW.Native]::mouse_event(0x0004, 0, 0, 0, 0)
}

# 0. Put the window on-screen and in front.
$h = [IntPtr]$win.Current.NativeWindowHandle
[LW.Native]::SetWindowPos($h, [IntPtr]::Zero, 40, 30, 0, 0, 0x0001 -bor 0x0040) | Out-Null
Start-Sleep -Milliseconds 500
[LW.Native]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 700
Write-Output '  window moved on-screen'

# 1. Open Luma Studio.
if (-not (Click-Button 'Luma Studio')) {
    Write-Output '  FAIL no "Luma Studio" button - is the UI in English?'
    exit 1
}
Start-Sleep -Milliseconds 1700
Write-Output '  opened Luma Studio'

# 2. Scroll down, the way a user does before reaching the placement pad.
$s = Get-Scroller
if (-not $s) { Write-Output '  FAIL the Studio page has no scrollable pane'; exit 1 }
$s.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, 62)
Start-Sleep -Milliseconds 1100
$before = $s.Pat.Current.VerticalScrollPercent
Write-Output ('  scrolled to {0:N0}%' -f $before)
if ($before -lt 20) {
    Write-Output '  FAIL could not scroll down, so the test would prove nothing'
    exit 1
}

# 3. Find the placement pad from its label and click a cell that is not the current one.
$label = Get-PositionLabel
if (-not $label) {
    Write-Output '  SKIP the placement label was not found in the automation tree'
    $t = Get-Texts
    Write-Output ('  Text elements seen: {0}' -f $t.Count)
    exit 2
}
Write-Output ('  current placement "{0}" at {1},{2} ({3}x{4})' -f $label.Name,
              $label.Left, $label.Top, $label.Width, $label.Height)

# The pad is 126x92 and sits to the LEFT of the label, vertically centred on it.
$padLeft = $label.Left - 16 - 126
$padTop  = $label.Top + [int]($label.Height / 2) - 46

$cells = @(
    @{ Name = 'top left';     X = $padLeft + 21; Y = $padTop + 15 },
    @{ Name = 'bottom right'; X = $padLeft + 105; Y = $padTop + 77 }
)

$picked = $cells[0]
if ($label.Name -eq 'Top left' -or $label.Name -eq 'Kiri atas') { $picked = $cells[1] }

Write-Output ('  clicking the "{0}" cell at {1},{2}' -f $picked.Name, $picked.X, $picked.Y)
Click-At $picked.X $picked.Y
Start-Sleep -Milliseconds 2000

$s2 = Get-Scroller
if (-not $s2) { Write-Output '  FAIL the page lost its scroll pane after the click'; exit 1 }
$after = $s2.Pat.Current.VerticalScrollPercent
Write-Output ('  scroll {0:N0}% -> {1:N0}%' -f $before, $after)

$label2 = Get-PositionLabel
if ($label2) { Write-Output ('  placement is now "{0}"' -f $label2.Name) }

if ($after -lt 20) {
    Write-Output '  FAIL the page jumped back to the top - the reported bug is still there'
    exit 1
}
$drift = [math]::Abs($after - $before)
if ($drift -gt 25) {
    Write-Output ('  FAIL the scroll moved by {0:N0} points' -f $drift)
    exit 1
}

Write-Output '  PASS choosing a placement keeps the scroll position'
exit 0
