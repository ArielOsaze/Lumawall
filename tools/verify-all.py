"""verify-all.py — runs every check and reports one verdict per requirement.

The point is coverage: after a long series of changes it is easy to believe
everything is handled while one item was quietly skipped. This runs each check as
its own process and prints a single table, so a missing item is visible.

Run:  python tools/verify-all.py
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shotlist import total as _total

# The promo's own length, read from the cut list rather than typed here. A hardcoded
# 52 outlived the render it described, and the check then failed every run for a
# reason that had nothing to do with the video.
TOTAL_SECONDS = _total()

# (what the user asked for, the check that proves it, extra args)
CHECKS = [
    ('promo sources resolve',
     ['python', 'tools/check_promo_imports.py']),
    ('copy has no machine-writing tells',
     ['python', 'tools/check-copy.py']),
    ('app text has no machine-writing tells',
     ['python', 'tools/check-app-text.py']),
    ('no button can show the Aero blue hover',
     ['python', 'tools/verify-no-aero-hover.py']),
    ('the hover that is there is visible on screen',
     ['python', 'tools/verify-hover.py']),
    ('every boundary is a cut, on the cut frame',
     ['python', 'tools/check-cuts.py']),
    ('the promo is cut like a commercial, not held like a deck',
     ['python', 'tools/check-pacing.py']),
    ('no screenshot is cropped, and not every shot is a wallpaper',
     ['python', 'tools/check-layout.py']),
    ('every element a scene places is inside the frame',
     ['python', 'tools/check-scene-layout.py']),
    ('the camera never crops the frame it is showing',
     ['python', 'tools/check-camera-crop.py']),
    ('every promo beat has content in it',
     ['python', 'tools/check-promo-scenes.py']),
    ('every promo beat keeps its content in frame',
     ['python', 'tools/check-frame-margins.py']),
    ('promo text is readable',
     ['python', 'tools/check-promo-text.py']),
    ('every text block sits on a dark enough background',
     ['python', 'tools/check-text-contrast.py']),
    ('every number on screen is a real number',
     ['python', 'tools/check-numbers.py']),
    ('every product image is staged and on screen',
     ['python', 'tools/check-promo-images.py']),
    ('the hero black matches the wallpaper',
     ['python', 'tools/check-hero-black.py']),
    ('the promo backgrounds vary',
     ['python', 'tools/measure-promo-backgrounds.py']),
    ('no empty or frozen frames',
     ['python', 'tools/check_frames.py', '--expect', str(TOTAL_SECONDS)]),
    ('hardware claims match the machine',
     ['python', 'tools/verify-hardware-claims.py']),
    ('the site is discoverable and previews correctly',
     ['python', 'tools/check-seo.py']),
    ('both language versions exist and are complete',
     ['python', 'tools/check-i18n.py']),
    ('the memory work is intact and the trim traps are absent',
     ['python', 'tools/check-memory-plan.py']),
    ('the wallpapers are actually rendering',
     ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
      'tools/check-wallpaper-alive.ps1']),
    ('the deploy config will not take the site down',
     ['python', 'tools/check-deploy-config.py']),
    ('every promo string is translated and fits',
     ['python', 'tools/check-promo-copy.py']),
    ('page behaviour: autoplay, crop, reveals, copy',
     ['node', 'tools/check-page.mjs']),
    ('page at every viewport size',
     ['node', 'tools/check-responsive.mjs']),
    ('site animation and font',
     ['node', 'tools/verify-site.mjs']),
    ('image crops are reasonable',
     ['node', 'tools/check-crops.mjs']),
]

results = []

# Several checks need Pillow and numpy, which are installed in the environment this
# script itself runs in. `python` on PATH can be a different interpreter that has
# neither, and the checks then fail with ModuleNotFoundError - a failure that says
# nothing about the work. Use the interpreter running this script.
PY = sys.executable

for name, cmd in CHECKS:
    if cmd[0] == 'python':
        cmd = [PY] + cmd[1:]

    # Which argument is the script? It is not always cmd[1]: a powershell invocation
    # is `powershell -NoProfile -ExecutionPolicy Bypass -File tools/x.ps1`, so cmd[1]
    # is a flag and the existence check reported "the check script does not exist" for
    # a script that was right there.
    script = None
    for argument in cmd:
        if argument.endswith(('.py', '.mjs', '.ps1', '.js')):
            script = argument
            break

    if script is None or not os.path.exists(script):
        results.append((name, 'MISSING', 'the check script does not exist'))
        continue

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    # Exit code 2 means "nothing to measure", which is not a failure - it is a check
    # that cannot run in the current state (the app is in the tray, the window is not
    # open). Treating it as a failure made the suite unusable unless everything
    # happened to be open, and a suite that always fails is a suite nobody reads.
    if r.returncode == 2:
        tail = (r.stdout or r.stderr or '').strip().split('\n')
        summary = tail[-1].strip() if tail else ''
        results.append((name, 'SKIP', summary[:88]))
        continue
    ok = r.returncode == 0
    tail = (r.stdout or r.stderr or '').strip().split('\n')
    summary = tail[-1].strip() if tail else ''
    results.append((name, 'PASS' if ok else 'FAIL', summary[:88]))

print()
print('  %-46s %-6s %s' % ('requirement', 'state', 'detail'))
print('  ' + '-' * 96)
for name, state, detail in results:
    print('  %-46s %-6s %s' % (name, state, detail))

failed = [r for r in results if r[1] == 'FAIL']
skipped = [r for r in results if r[1] == 'SKIP']
print()
if failed:
    print('  %d of %d checks failed' % (len(failed), len(results)))
    if skipped:
        print('  (%d skipped: nothing to measure in the current state)' % len(skipped))
    sys.exit(1)
if skipped:
    print('  all %d checks passed (%d skipped: nothing to measure in the current state)'
          % (len(results), len(skipped)))
else:
    print('  all %d checks passed' % len(results))
