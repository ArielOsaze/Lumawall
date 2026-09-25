"""trim-ui-shots.py — crops the app screenshots to the part that shows the UI.

Why: a screenshot of a real app window includes whatever empty space the window
happens to have. The Displays page fills its top half and leaves the bottom half
blank, so on the site that card looked broken rather than sparse - a review read
it as a failed image load.

Trimming to the content is what a screenshot for a marketing page should be: the
window chrome and the useful area, not the app's whitespace.

Run:  python tools/trim-ui-shots.py
"""

import os
import subprocess
import sys

# (file, fraction of the height to keep)
#
# The fractions were chosen by looking at each screenshot: the point is to cut
# below the last row of content, never through it.
CROPS = [
    ('site/assets/shots/ui-displays.png', 0.62),
    ('site/assets/shots/ui-library.png', 0.86),
    ('site/assets/shots/ui-discover.png', 0.88),
    ('site/assets/shots/ui-performance.png', 0.84),
]


def dimensions(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    if not out:
        return None
    w, h = out.split(',')[:2]
    return int(w), int(h)


print('  trimming the app screenshots:')
for path, keep in CROPS:
    if not os.path.exists(path):
        print('    missing: %s' % path)
        continue

    dims = dimensions(path)
    if not dims:
        print('    cannot read: %s' % path)
        continue
    w, h = dims
    new_h = int(h * keep)
    # Even numbers keep the encoder happy and avoid a half-pixel row.
    new_h -= new_h % 2

    tmp = path + '.tmp.png'
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-i', path,
         '-vf', 'crop=%d:%d:0:0' % (w, new_h),
         tmp],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print('    failed: %s' % path)
        print('     ', r.stderr.strip()[:200])
        continue

    os.replace(tmp, path)
    print('    %-44s %dx%d -> %dx%d  (%d%% kept)' % (
        path.split('/')[-1], w, h, w, new_h, int(keep * 100)))

print()
print('  done')
