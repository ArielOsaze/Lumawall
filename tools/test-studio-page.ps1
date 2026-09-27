# Click the Luma Studio nav entry the way a user does, then report what happened.
#
# This exists because the page crashed on open - SectionHeader(title, null, null)
# threw ArgumentNullException("handler") - and nothing in the build, the log at
# startup, or a smoke test that never opened the page would have caught it. The
# only way to know the page works is to open it.
#
# UI Automation is used rather than a screen coordinate so the click lands on the
# button whatever the window position is, and so a failure to find the button is
# reported as "not found" rather than silently clicking whatever is at that pixel.

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes

$proc = Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) {
    Write-Output '  FAIL  LumaWall is not running'
    exit 1
}

Write-Output ('  LumaWall pid {0}' -f $proc.Id)

$root = [System.Windows.Automation.AutomationElement]::RootElement
$condition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)

# The window can take a moment to appear and to finish building its tree.
$window = $null
for ($i = 0; $i -lt 30 -and -not $window; $i++) {
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
    if (-not $window) { Start-Sleep -Milliseconds 500 }
}
if (-not $window) {
    Write-Output '  FAIL  the app window was not found'
    exit 1
}
Write-Output ('  window: "{0}"' -f $window.Current.Name)

# The rail buttons carry their label as the automation name, so the page can be
# found by the same words a user reads.
$target = 'Luma Studio'
$buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, $target)
$button = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)

if (-not $button) {
    Write-Output ('  FAIL  no element named "{0}" - the rail label is not reaching the UI tree' -f $target)

    # List what the rail does expose, so the next run is not another guess.
    Write-Output '  rail entries actually present:'
    $all = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($element in $all) {
        if ($element.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $element.Current.Name) {
            Write-Output ('    "{0}"' -f $element.Current.Name)
        }
    }
    exit 1
}

Write-Output ('  found  : "{0}" ({1})' -f $button.Current.Name, $button.Current.ControlType.ProgrammaticName)

$pattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
$pattern.Invoke()
Write-Output '  clicked'

Start-Sleep -Seconds 3

# Still alive? A WPF exception inside a click handler is caught by the dispatcher
# and logged, and the window survives - so "is it running" is not enough on its
# own. The caller checks the log for UNHANDLED UI EXCEPTION; this reports the
# process state and which page the window now shows.
$still = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
if ($still) {
    Write-Output ('  process alive: yes (responding={0})' -f $still.Responding)
} else {
    Write-Output '  process alive: NO - it exited when the page opened'
    exit 1
}

# Read the visible text of the page to confirm the copy rendered as words rather
# than as translation keys. A key that is missing from the dictionary is shown
# verbatim, which is how "studio.brightness" reached the screen.
$texts = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Text)))
$seen = @()
foreach ($t in $texts) { if ($t.Current.Name) { $seen += $t.Current.Name } }

$rawKeys = $seen | Where-Object { $_ -match '^(studio|timer|filter|flip|fit)\.[a-zA-Z]+$' }
if ($rawKeys) {
    Write-Output '  FAIL  untranslated keys are visible on the page:'
    $rawKeys | Select-Object -Unique | ForEach-Object { Write-Output ('    {0}' -f $_) }
    exit 1
}

Write-Output '  no raw translation keys on screen'

foreach ($want in @('Luma Studio', 'Warna', 'Filter', 'Timer desktop', 'Bentuk', 'Penempatan')) {
    $found = $seen | Where-Object { $_ -eq $want }
    if ($found) { Write-Output ('  shows  : "{0}"' -f $want) }
    else { Write-Output ('  missing: "{0}"' -f $want) }
}

Write-Output '  OK'
exit 0
