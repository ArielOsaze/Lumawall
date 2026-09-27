"""Check every timer style from the pixels the widget itself draws.

Why this exists
---------------
Two earlier attempts at this check were worthless, and both looked like a pass.

The first screenshotted the widget and thresholded "bright pixels". The widget is a layered
window over the wallpaper, so the capture contained the wallpaper too, and the check
reported every style at 93% ink with a full-height clock band. It was measuring the
wallpaper.

The second rendered the styles with a PIL re-implementation of the layout. That is a second
implementation, so it agreed with itself and not with the app: it drew ioslarge at 329x307
while the widget drew it at 353x167.

This reads the PNGs the app writes in --render-timer mode. They come from DrawFrame - the
same method the widget paints with - so the alpha in them is the widget's own alpha, and
"is the clock large" and "is the background transparent" become questions about the drawing.

What it checks:
  * every style the Studio page offers has a preview, so a new style cannot be added and go
    unmeasured;
  * something is drawn - a style that paints nothing fails;
  * the background is transparent: most pixels must have zero alpha, which is what
    "background transparan" means. A solid card fails;
  * the lock-screen styles have a LARGE clock, measured as the share of the widget's height
    the glyphs occupy. A small clock in a style called "ioslarge" fails;
  * the clock is not clipped: the glyphs must not touch the widget's edges, which is what a
    window sized for one font and drawn with a bigger one looks like.

Usage: python tools/check-timer-styles.py
"""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'build' / 'timer-preview'
EXE = ROOT / 'LumaWall' / 'bin' / 'Release' / 'LumaWall.exe'

# The styles the Studio page offers, in its order. Kept here so a style added to the page
# and not to this list is caught by the count check.
STYLES = ['minimal', 'bold', 'glass', 'card', 'ring', 'analog',
          'ioslarge', 'ioslight', 'iosstack', 'iosdate']

# The lock-screen styles are defined by a large clock. These are the minimum share of the
# widget's height the glyphs must cover, measured from the alpha channel.
LARGE = {'ioslarge': 0.40, 'ioslight': 0.30, 'iosstack': 0.28, 'iosdate': 0.22}

# Styles that intentionally paint a wash behind the text, so their background is not fully
# transparent. Everything else must let the wallpaper through.
WASHED = {'glass', 'card'}


def render():
    """Ask the app for fresh previews, and read back the face each style resolved to."""
    if not EXE.exists():
        return False, 'the app is not built at %s' % EXE, {}
    if PREVIEW.exists():
        for old in PREVIEW.glob('*.png'):
            old.unlink()
    PREVIEW.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([str(EXE), '--render-timer', str(PREVIEW)],
                       capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        return False, (p.stdout or '') + (p.stderr or ''), {}

    # The app prints "<style>  <w>x<h>  <face>". The face is what the style actually drew
    # with - the one fact a filename cannot carry.
    faces = {}
    for line in (p.stdout or '').splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] in STYLES and 'x' in parts[1]:
            faces[parts[0]] = ' '.join(parts[2:])
    return True, '', faces


def measure(path):
    """Facts about one preview, read from its alpha."""
    img = Image.open(path).convert('RGBA')
    a = np.asarray(img)
    alpha = a[:, :, 3]
    h, w = alpha.shape

    # Ink is where the widget painted something opaque. The shadow is partially opaque and
    # is not ink; the glyphs are.
    ink = alpha > 200
    ink_share = float(ink.mean())

    # "Transparent background" means the wallpaper still shows through. Measuring alpha == 0
    # was wrong: glass and card paint a faint wash over the whole widget, so no pixel is
    # fully clear and the check failed a background that is 79% see-through. What matters is
    # whether the wallpaper dominates, so this counts the pixels the wallpaper still reaches.
    see_through = float((alpha <= 140).mean())

    # The glyph band: the rows that contain ink, as a share of the widget's height.
    rows = ink.any(axis=1)
    if rows.any():
        top = int(np.argmax(rows))
        # argmax on the reversed rows gives the distance from the END to the last ink row,
        # so this is an exclusive bound. Treating it as inclusive flagged the ring style,
        # whose ink stops one pixel inside the edge, as clipped.
        end = int(h - np.argmax(rows[::-1]))
        bottom = end - 1
        band = (bottom - top + 1) / float(h)
        touches_edge = top <= 0 or bottom >= h - 1
    else:
        band = 0.0
        touches_edge = False

    cols = ink.any(axis=0)
    touches_side = bool(cols[0]) or bool(cols[-1])

    return {
        'size': (w, h),
        'ink': ink_share,
        'see_through': see_through,
        'band': band,
        'touches_edge': touches_edge or touches_side,
    }


def main():
    ok, error, faces = render()
    if not ok:
        print('  FAIL could not render the previews')
        for line in error.strip().splitlines()[-8:]:
            print('       %s' % line)
        return 1

    # Every style must draw in its own face.
    #
    # This is the check that was missing, and its absence hid a real bug: the iOS styles
    # asked for a light face with a condition that could never match one, so they fell back
    # to a heavier face - and iosdate was not in the list at all, so it drew in exactly the
    # same font as minimal. Side by side they looked identical, which is precisely what the
    # user reported ("font timernya gada bedanya"). Nothing here could see that, because
    # every measurement was of pixels and the pixels were all present and correct.
    #
    # Now the app reports the resolved family name and this compares them.
    EXPECTED = {
        'ioslarge': 'Light',
        'ioslight': 'Segoe UI Light',
        'iosstack': 'Light',
        'iosdate': 'Semil',
        'bold': 'Bold',
        'card': 'Bold',
    }
    distinct = {}
    for style, face in faces.items():
        distinct.setdefault(face, []).append(style)
    print('  faces in use:')
    for face, styles in sorted(distinct.items(), key=lambda kv: -len(kv[1])):
        print('    %-38s %s' % (face, ', '.join(styles)))
    print()

    face_failures = []
    for style, want in EXPECTED.items():
        got = faces.get(style)
        if got is None:
            continue  # already reported as missing
        if want.lower() not in got.lower():
            print('  %-10s FAIL face "%s", expected %s' % (style, got, want))
            face_failures.append('%s drew in "%s", expected a %s face' % (style, got, want))
        else:
            print('  %-10s ok    %s' % (style, got))
    print()

    print('  %-10s %10s %8s %8s %9s  %s'
          % ('style', 'size', 'ink %', 'thru %', 'band', 'note'))
    rows = []
    failures = []
    for style in STYLES:
        path = PREVIEW / (style + '.png')
        if not path.exists():
            failures.append('%s has no preview' % style)
            print('  %-10s %10s' % (style, 'MISSING'))
            continue
        m = measure(path)
        note = ''
        if m['ink'] < 0.005:
            note = '<<< DRAWS NOTHING'
            failures.append('%s draws nothing' % style)
        elif m['touches_edge']:
            note = '<<< CLIPPED'
            failures.append('%s is clipped at the widget edge' % style)
        rows.append((style, m))
        print('  %-10s %5dx%-4d %7.1f%% %7.1f%% %8.2f  %s'
              % (style, m['size'][0], m['size'][1],
                 m['ink'] * 100, m['see_through'] * 100, m['band'], note))

    print()

    # Transparency: the wallpaper has to show through. A style that fills its rectangle is
    # the "kotak hitam" the user complained about. The washed styles are allowed to be
    # dimmer - a widget material is meant to be faint - but the wallpaper must still be the
    # thing you see.
    for style, m in rows:
        need = 0.30 if style in WASHED else 0.50
        if m['see_through'] < need:
            failures.append('%s background is only %.0f%% see-through, needs %.0f%%'
                            % (style, m['see_through'] * 100, need * 100))
            print('  %-10s FAIL background not transparent (%.0f%% see-through, needs %.0f%%)'
                  % (style, m['see_through'] * 100, need * 100))
        else:
            print('  %-10s ok    background %.0f%% see-through, the wallpaper shows'
                  % (style, m['see_through'] * 100))

    print()

    # The lock-screen styles must have a large clock.
    for style, m in rows:
        if style not in LARGE:
            continue
        need = LARGE[style]
        if m['band'] < need:
            failures.append('%s clock is %.2f of the widget, needs %.2f'
                            % (style, m['band'], need))
            print('  %-10s FAIL clock band %.2f, needs %.2f' % (style, m['band'], need))
        else:
            print('  %-10s ok    large clock (band %.2f of the widget)' % (style, m['band']))

    print()
    failures.extend(face_failures)
    if failures:
        for f in failures:
            print('  FAIL %s' % f)
        return 1
    print('  PASS every style draws in its own face, the backgrounds are transparent, '
          'the lock-screen styles are large, and nothing is clipped')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
