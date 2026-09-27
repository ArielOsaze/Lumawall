# Scroll the Luma Studio page to a given percentage, so a card below the fold can be seen.
#
# Usage: powershell -File tools/scroll-studio.ps1 -Percent 60

param([int]$Percent = 60)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]

$root = $auto::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')
$win = $root.FindFirst($scope::Children, $cond)
if (-not $win) { Write-Output '  the LumaWall window was not found'; exit 1 }

# Find the tallest vertically-scrollable pane: that is the page.
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

if (-not $best) { Write-Output '  no scrollable pane found'; exit 1 }

$best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, $Percent)
Start-Sleep -Milliseconds 800
Write-Output ('  scrolled to {0:N0}%' -f $best.Pat.Current.VerticalScrollPercent)
exit 0
