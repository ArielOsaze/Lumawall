"""verify-all.py — runs every check and reports one verdict per requirement.

The point is coverage: after a long series of changes it is easy to believe
everything is handled while one item was quietly skipped. This runs each check as
its own process and prints a single table, so a missing item is visible.

Run:  python tools/verify-all.py
"""

import os
import subprocess
import sys

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
    ('the whip blur matches the motion',
     ['python', 'tools/check-whip-blur.py']),
    ('transitions never double-expose',
     ['python', 'tools/check-transition-curve.py']),
    ('every promo beat shows a wallpaper',
     ['python', 'tools/check-promo-scenes.py', 'site/assets/video/lumawall-promo.mp4']),
    ('no empty or frozen frames',
     ['python', 'tools/check_frames.py', 'site/assets/video/lumawall-promo.mp4', '--expect', '52']),
    ('hardware claims match the machine',
     ['python', 'tools/verify-hardware-claims.py']),
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
for name, cmd in CHECKS:
    if cmd[0] == 'python' and not os.path.exists(cmd[1]):
        results.append((name, 'MISSING', 'the check script does not exist'))
        continue
    if cmd[0] == 'node' and not os.path.exists(cmd[1]):
        results.append((name, 'MISSING', 'the check script does not exist'))
        continue

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    ok = r.returncode == 0
    tail = (r.stdout or r.stderr or '').strip().split('\n')
    summary = tail[-1].strip() if tail else ''
    results.append((name, 'PASS' if ok else 'FAIL', summary[:88]))

print()
print('  %-46s %-6s %s' % ('requirement', 'state', 'detail'))
print('  ' + '-' * 96)
for name, state, detail in results:
    print('  %-46s %-6s %s' % (name, state, detail))

failed = [r for r in results if r[1] != 'PASS']
print()
if failed:
    print('  %d of %d checks failed' % (len(failed), len(results)))
    sys.exit(1)
print('  all %d checks passed' % len(results))
