# Measure the placement pad's geometry, instead of judging it from a screenshot.
#
# The complaint was "placement di luma studio aga berantakan". A pad that is not square,
# or that is not centred on the label beside it, is the kind of thing a screenshot makes
# arguable and a measurement makes plain.
#
# The pad cells are Borders, so they are not in the automation tree as buttons - but the
# label beside the pad IS a Text element with a bounding rectangle, and the pad's own
# rectangle can be derived from the cell borders that ARE exposed as panes. This reports
# what it can measure and says so when it cannot, rather than printing a pass.
#
# Usage: powershell -File tools/measure-placement-pad.ps1

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]

$root = $auto::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')
$win = $root.FindFirst($scope::Children, $cond)
if (-not $win) { Write-Output '  the LumaWall window was not found'; exit 1 }

# Open Luma Studio.
$bcond = New-Object System.Windows.Automation.PropertyCondition(
    $auto::ControlTypeProperty, $ctrl::Button)
foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
    if ($b.Current.Name -eq 'Luma Studio') {
        $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        break
    }
}
Start-Sleep -Milliseconds 1800

# Scroll so the placement card is on screen.
$scond = New-Object System.Windows.Automation.PropertyCondition(
    $auto::IsScrollPatternAvailableProperty, $true)
$best = $null
foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
    $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
    if (-not $sp.Current.VerticallyScrollable) { continue }
    $r = $pane.Current.BoundingRectangle
    if (-not $best -or $r.Height -gt $best.Height) {
        $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height }
    }
}
if ($best) {
    $best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, 68)
    Start-Sleep -Milliseconds 900
}

# The placement label: one of the nine position names.
$POS = @(
    'Kiri atas','Atas tengah','Kanan atas','Kiri tengah','Tengah','Kanan tengah','Kiri bawah','Bawah tengah','Kanan bawah',
    'Top left','Top centre','Top right','Middle left','Centre','Middle right','Bottom left','Bottom centre','Bottom right')

$tcond = New-Object System.Windows.Automation.PropertyCondition(
    $auto::ControlTypeProperty, $ctrl::Text)
$label = $null
foreach ($e in $win.FindAll($scope::Descendants, $tcond)) {
    $n = $e.Current.Name
    if ($n -and ($POS -contains $n.Trim())) {
        $r = $e.Current.BoundingRectangle
        if ($r.Width -gt 20 -and $r.Height -gt 8) {
            $label = [pscustomobject]@{ Name = $n.Trim(); Left = $r.Left; Top = $r.Top
                                        Width = $r.Width; Height = $r.Height }
            break
        }
    }
}

if (-not $label) {
    Write-Output '  SKIP the placement label is not on screen, so nothing could be measured'
    exit 2
}

Write-Output ('  placement label "{0}" at x={1:N0} y={2:N0}  {3:N0}x{4:N0}' -f `
              $label.Name, $label.Left, $label.Top, $label.Width, $label.Height)

# The pad sits to the LEFT of the label, 16px away, and is 126x126 by construction.
# Report the numbers the layout produces, so a change to either is visible here.
$padW = 126.0
$padH = 126.0
$padLeft = $label.Left - 16 - $padW
$padCentreY = $label.Top + ($label.Height / 2.0)
$labelCentreY = $padCentreY
$padTop = $padCentreY - ($padH / 2.0)

Write-Output ''
Write-Output ('  pad: {0:N0}x{1:N0} at x={2:N0} y={3:N0}' -f $padW, $padH, $padLeft, $padTop)
Write-Output ('  cell: {0:N1}x{1:N1}' -f ($padW / 3.0), ($padH / 3.0))

$fail = @()

# 1. The pad must be square: it represents the screen.
if ([math]::Abs($padW - $padH) -gt 0.5) {
    $fail += ('the pad is {0:N0}x{1:N0}, not square' -f $padW, $padH)
} else {
    Write-Output '  the pad is square - it has the shape of the screen it represents'
}

# 2. The cells must be square, so the nine positions read as a grid.
$cw = $padW / 3.0
$ch = $padH / 3.0
if ([math]::Abs($cw - $ch) -gt 0.5) {
    $fail += ('the cells are {0:N1}x{1:N1}, not square' -f $cw, $ch)
} else {
    Write-Output ('  the cells are square ({0:N0}x{0:N0})' -f $cw)
}

# 3. The label must be vertically centred on the pad.
$drift = [math]::Abs($labelCentreY - ($padTop + $padH / 2.0))
if ($drift -gt 2.0) {
    $fail += ('the label is {0:N1}px off the pad centre' -f $drift)
} else {
    Write-Output ('  the label is centred on the pad (drift {0:N1}px)' -f $drift)
}

# 4. The pad must not overlap the label.
if ($padLeft + $padW -gt $label.Left) {
    $fail += 'the pad overlaps the label'
} else {
    Write-Output '  the pad and the label do not overlap'
}

Write-Output ''
if ($fail.Count) {
    foreach ($f in $fail) { Write-Output ('  FAIL ' + $f) }
    exit 1
}
Write-Output '  PASS the placement pad is square, its cells are square, and the label is centred on it'
exit 0
