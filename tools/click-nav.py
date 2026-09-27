"""Click a LumaWall nav button by its label, using UI Automation.

Why this exists
---------------
Clicking by coordinates is guesswork: the rail is built at runtime, the window has a
border, and a near miss silently clicks the wrong page (or nothing) while the screenshot
still looks plausible. UI Automation asks the app where the button actually is and
invokes it, so "go to the Catalog page" either happens or fails loudly.

Usage: python tools/click-nav.py Catalog
"""
import sys
import time

import clr  # noqa: F401  (pythonnet, installed with the checker toolchain)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'Catalog'

    clr.AddReference('UIAutomationClient')
    clr.AddReference('UIAutomationTypes')
    from System.Windows.Automation import (  # noqa: E402
        AutomationElement, TreeScope, Condition, PropertyCondition,
        AutomationProperty, InvokePattern, ScrollItemPattern, AutomationPattern,
    )

    root = AutomationElement.RootElement
    cond = PropertyCondition(AutomationElement.NameProperty, 'LumaWall')
    win = root.FindFirst(TreeScope.Children, cond)
    if win is None:
        print('  the LumaWall window was not found')
        return 1

    # The nav buttons are Buttons whose Name is the label.
    bcond = PropertyCondition(AutomationElement.ControlTypeProperty,
                              __import__('System.Windows.Automation').Windows.Automation.ControlType.Button)
    buttons = win.FindAll(TreeScope.Descendants, bcond)
    names = [b.Current.Name for b in buttons]
    hit = None
    for b in buttons:
        if b.Current.Name == label:
            hit = b
            break

    if hit is None:
        print('  no button named %r. Buttons present: %s' % (label, names))
        return 1

    # The window may be minimised; make sure it is on screen first.
    try:
        win.SetFocus()
    except Exception:
        pass
    time.sleep(0.4)

    pat = hit.GetCurrentPattern(InvokePattern.Pattern)
    pat.Invoke()
    print('  invoked %r' % label)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
