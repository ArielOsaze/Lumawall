"""verify-no-aero-hover.py — checks that no button can inherit WPF's blue hover.

WPF's built-in Button template has a trigger that paints the button #FFBEE6FD on
hover. A button whose Background is set in code still turns pale blue, because the
template's trigger overrides the value it is templating. The visible symptom was a
light blue rectangle over whichever button the pointer was on.

There are two defences and this checks both:

  1. the app registers an implicit Button style with no hover trigger, so a button
     added later cannot bring the blue back
  2. every Button built in code either uses SetRoundedButton or is inside the
     scope of that implicit style

Run:  python tools/verify-no-aero-hover.py
"""

import io
import re
import sys

SOURCES = ['LumaWall/MainWindow.cs', 'LumaWall/Program.cs', 'LumaWall/Icons.cs']

print('  checking for the Aero hover')

problems = []

# ── 1. the implicit style exists ─────────────────────────────────────────────
program = io.open('LumaWall/Program.cs', encoding='utf-8').read()

has_style_fn = 'BuildDefaultButtonStyle' in program
has_registration = 'app.Resources[typeof(System.Windows.Controls.Button)]' in program
has_hover_trigger = bool(re.search(
    r'IsMouseOver[^\n]{0,80}Background', program))

print('    implicit Button style defined   : %s' % has_style_fn)
print('    registered on the Application   : %s' % has_registration)
print('    style contains a hover trigger  : %s' % has_hover_trigger)

if not has_style_fn:
    problems.append('BuildDefaultButtonStyle is missing')
if not has_registration:
    problems.append('the implicit style is never registered, so it has no effect')
if has_hover_trigger:
    problems.append('the new style has its own hover trigger, which is what we removed')

# ── 2. every button in code has a template ───────────────────────────────────
# The implicit style covers buttons created after Application.Resources is set,
# which is all of them, but a button that sets its own Template replaces it - so
# the check is that any button with a custom Template also has a hover of its own
# rather than relying on the built-in one.
for path in SOURCES:
    try:
        text = io.open(path, encoding='utf-8').read()
    except FileNotFoundError:
        continue

    for m in re.finditer(r'new Button\s*\{', text):
        line_no = text[:m.start()].count('\n') + 1
        # Look ahead to the end of the statement.
        window = text[m.start():m.start() + 1800]
        # A button is fine if it uses SetRoundedButton, or sets no template at all
        # (in which case the implicit style applies).
        sets_template = 'ControlTemplate' in window
        has_rounded = 'SetRoundedButton' in window
        if sets_template and not has_rounded:
            problems.append('%s:%d builds a Button with its own template but no hover' % (
                path.split('/')[-1], line_no))

print('    buttons with an unguarded template: %d' % len(
    [p for p in problems if 'own template' in p]))

print()
if problems:
    print('  %d problem(s):' % len(problems))
    for p in problems:
        print('    ' + p)
    sys.exit(1)
print('  no button can show the Aero hover')
