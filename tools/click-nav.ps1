# Click a LumaWall nav button by its label, using UI Automation.
#
# Why this exists: clicking by coordinates is guesswork. The nav rail is built at
# runtime, the window has a border, and a near miss silently clicks the wrong page
# while the screenshot still looks plausible. UI Automation asks the app where the
# button actually is and invokes it, so "go to the Catalog page" either happens or
# fails loudly.
#
# Usage: powershell -File tools/click-nav.ps1 -Label Catalog

param([string]$Label = 'Catalog')

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]

$root = $auto::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')
$win = $root.FindFirst($scope::Children, $cond)
if (-not $win) { Write-Output '  the LumaWall window was not found'; exit 1 }

$bcond = New-Object System.Windows.Automation.PropertyCondition(
    $auto::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
$buttons = $win.FindAll($scope::Descendants, $bcond)

$names = @()
$hit = $null
foreach ($b in $buttons) {
    $n = $b.Current.Name
    $names += $n
    if ($n -eq $Label -and -not $hit) { $hit = $b }
}

if (-not $hit) {
    Write-Output ("  no button named '{0}'. Buttons present: {1}" -f $Label, ($names -join ', '))
    exit 1
}

try { $win.SetFocus() } catch { }
Start-Sleep -Milliseconds 400

$pat = $hit.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
$pat.Invoke()
Write-Output ("  invoked '{0}'" -f $Label)
exit 0
