"""make-og-card.py — builds the image that appears when the link is shared.

Why this file matters: og:image was pointing at a wallpaper, at a relative path,
at full wallpaper dimensions. Three separate problems, and all three fail
silently - the page loads, the link works, and the preview is a bare URL with no
thumbnail.

  · a relative URL is resolved against the crawler's own base, not the page's
  · a 1920x1080 image is cropped by every platform, and the crop is centred, so
    the subject can be cut in half
  · a wallpaper with no branding says nothing about what the link is

This composes 1200x630 - the size every platform crops from - from the product's
own assets: a wallpaper, the mark, the wordmark, and the one claim that matters.
The subject sits in the right third so a centre crop keeps it.

Run:  python tools/make-og-card.py
"""

import os
import subprocess
import sys

OUT = 'site/assets/shots/og-card.png'
W, H = 1200, 630

WALL = 'site/assets/shots/hero-bg.jpg'
MARK = 'site/assets/logo/logo-150.png'

for path in (WALL, MARK):
    if not os.path.exists(path):
        sys.exit('missing %s' % path)

# The wallpaper is 2:1 and the card is 1.9:1, so almost nothing is cropped. The
# grade darkens it enough for the type without flattening it, and the vignette
# keeps the corners from competing with the wordmark.
grade = (
    f'scale={W}:{H}:force_original_aspect_ratio=increase,'
    f'crop={W}:{H},'
    'eq=brightness=-0.10:contrast=1.10:saturation=0.95,'
    'vignette=PI/4'
)

cmd = [
    'ffmpeg', '-v', 'error', '-y',
    '-i', WALL,
    '-vf', grade,
    '-frames:v', '1',
    OUT + '.base.png',
]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print('  ffmpeg failed:')
    print('   ', r.stderr.strip()[:500])
    sys.exit(1)

# Compose the type over the graded plate. Done in Python rather than with ffmpeg
# drawtext because drawtext needs a font file path and escaping, and a silent
# escaping mistake produces a card with no text on it.
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print('  Pillow is needed for the text overlay')
    print('  the graded plate is at %s.base.png' % OUT)
    sys.exit(1)

base = Image.open(OUT + '.base.png').convert('RGB')

# A soft dark plate behind the text block, so the type is readable wherever the
# wallpaper happens to be bright.
plate = Image.new('RGBA', (W, H), (0, 0, 0, 0))
pd = ImageDraw.Draw(plate)
for x in range(0, int(W * 0.72)):
    # Left to right: opaque enough to read on, clearing to nothing.
    a = int(196 * (1 - (x / (W * 0.72)) ** 1.5))
    pd.line([(x, 0), (x, H)], fill=(8, 9, 13, a))
base = Image.alpha_composite(base.convert('RGBA'), plate).convert('RGB')

draw = ImageDraw.Draw(base)

FONT_DIR = 'site/assets/fonts'
# The card needs a static weight; the variable font is used at its default.
FONT_CANDIDATES = [
    os.path.join(FONT_DIR, 'jakarta-latin.woff2'),
    'C:/Windows/Fonts/segoeui.ttf',
    'C:/Windows/Fonts/arial.ttf',
]


def load(size, bold=False):
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ── the safe zone ────────────────────────────────────────────────────────────
#
# Some platforms force a square crop and take it from the centre. Anything
# outside the centre 630x630 is therefore optional, so the mark, the claim and the
# figures all sit inside a column at x=150..640 and nothing essential lives near
# an edge.
SAFE_L, SAFE_R = 285, 915
X = 300

# The mark, with the wordmark beside it.
# The mark sits at the top of the safe zone, with the wordmark beside it. The
# mark is small because on a 1:1 crop every pixel of margin counts.
mark = Image.open(MARK).convert('RGBA').resize((56, 56), Image.LANCZOS)
base.paste(mark, (X, 104), mark)

f_word = load(36, bold=True)
f_sub = load(19)
f_claim = load(34, bold=True)
f_fig = load(21)

draw.text((X + 70, 110), 'LumaWall', font=f_word, fill=(245, 247, 248))
draw.text((X + 70, 152), 'Wallpaper hidup untuk Windows', font=f_sub, fill=(162, 170, 180))

# The claim, at the vertical centre so a square crop keeps it whole. Two lines,
# both starting at the safe-zone edge.
draw.text((X, 300), 'Wallpaper bergerak,', font=f_claim, fill=(245, 247, 248))
draw.text((X, 344), 'komputer tetap tenang', font=f_claim, fill=(255, 59, 87))

# The figures, stacked so they survive a square crop rather than spread to the
# edges where they would be cut.
y = 438
for line in ['5.000+ wallpaper', 'CPU di bawah 1%', 'Gratis, tanpa iklan']:
    draw.text((X, y), line, font=f_fig, fill=(198, 205, 214))
    y += 36

base.save(OUT, 'PNG', optimize=True)
os.remove(OUT + '.base.png')

print('  %s  (%d bytes, %dx%d)' % (OUT, os.path.getsize(OUT), W, H))
