# Press something in a WPF window, whether or not it exposes an InvokePattern.
#
# Why this is a script of its own: several controls on the Luma Studio page are Borders
# with a mouse handler rather than Buttons - the display rows, the shape tiles, the
# position dots, the toggle switches. They are the right control for the job (a Button
# cannot show a live preview), but UI Automation reports them without an InvokePattern,
# so a test that only calls Invoke() cannot press them and silently skips the controls
# that are most likely to be broken.
#
# The fallback is a real mouse click at the element's own centre. That is what a user
# does, so it exercises the same code path - and it is why the window is brought to the
# foreground first: a click lands on whatever is on top at those coordinates.

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Mouse {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    public const uint LeftDown = 0x0002;
    public const uint LeftUp = 0x0004;
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(40);
        mouse_event(LeftDown, 0, 0, 0, UIntPtr.Zero);
        System.Threading.Thread.Sleep(30);
        mouse_event(LeftUp, 0, 0, 0, UIntPtr.Zero);
    }
}
"@

function Invoke-Element {
    param($Element)
    # Prefer the pattern: it does not move the mouse, so it cannot miss.
    try {
        $pattern = $Element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $pattern.Invoke()
        return 'invoke'
    } catch { }

    # Fall back to a real click at the element's centre.
    $rect = $Element.Current.BoundingRectangle
    if ($rect.Width -le 0 -or $rect.Height -le 0) { throw 'the element has no size' }
    $x = [int]($rect.Left + $rect.Width / 2)
    $y = [int]($rect.Top + $rect.Height / 2)
    [Mouse]::Click($x, $y)
    return 'click'
}

function Find-Element {
    param($Window, [string]$Name)
    return $Window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, $Name)))
}

function Test-Flatten {
    # WPF puts the visible text of a composite control into child Text elements, and UI
    # Automation then reports the parent's Name as the concatenation - which is how
    # "Show a timer" becomes "Show a timer Shows a clock or countdown..." and stops
    # matching. So the search is by substring, not equality.
    param($Window, [string]$Contains)
    $all = $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($element in $all) {
        $name = $element.Current.Name
        if ($name -and $name -like ('*' + $Contains + '*')) { return $element }
    }
    return $null
}
