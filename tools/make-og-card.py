"""make-og-card.py — builds the image that appears when the link is shared.

Why this file matters: og:image was pointing at a wallpaper, at a relative path, at
full wallpaper dimensions. Three separate problems, and all three fail silently - the
page loads, the link works, and the preview is a bare URL with no thumbnail.

  · a relative URL is resolved against the crawler's own base, not the page's
  · a 1920x1080 image is cropped by every platform, and the crop is centred, so the
    subject can be cut in half
  · a wallpaper with no branding says nothing about what the link is

So the card is 1200x630 - the size every platform crops from - composed from the
product's own assets.

── the rewrite, and what it fixes ──────────────────────────────────────────

The first version scored 6.5/10 in review, with three specific faults:

  · "too much empty space - the left side has a large vertical strip of black that
    serves no purpose". The text column started at x=300 in a 1200px card and the
    plate faded out by 864, so a third of the card was a dark void.
  · "the feature list is too small for a thumbnail" - the three facts were set at
    21px, which is 7px when the card is shown at 400px wide in a feed.
  · "the gap between the headline and the feature list is quite large" - 94px of
    nothing between the claim and the facts.

All three are fixed by giving the text the card: the column starts at x=64, the facts
are set at 30px, and the vertical rhythm is tight. The subject moves right and the
plate is a full-height gradient rather than a fading strip, so the type sits on a
consistent dark field instead of on whatever part of the wallpaper is under it.

The measurements are in the code as named constants rather than inline numbers, so a
future change can see what it is moving.

Run:  python tools/make-og-card.py
"""

import os
import subprocess
import sys

OUT = 'site/assets/shots/og-card.png'
W, H = 1200, 630

# The assets are served with a content hash in the filename (`hero-bg.6609e553d0.jpg`),
# and the unhashed name only exists in the working tree between a build and a
# cache-bust. Resolving the stem rather than the exact name means this runs whether or
# not the cache-buster has been through - the first version hardcoded the plain name
# and failed with "missing site/assets/shots/hero-bg.jpg" the moment it had.
SHOTS = 'site/assets/shots'


def resolve(stem, exts=('.jpg', '.jpeg', '.png')):
    """The file for `stem`, hashed or not."""
    for ext in exts:
        plain = os.path.join(SHOTS, stem + ext)
        if os.path.exists(plain):
            return plain
    for f in sorted(os.listdir(SHOTS)):
        for ext in exts:
            if f.startswith(stem + '.') and f.endswith(ext) and not f.endswith('.bak'):
                return os.path.join(SHOTS, f)
    return None


WALL = resolve('hero-bg')
MARK = 'site/assets/logo/logo-150.png'

# ── the layout ───────────────────────────────────────────────────────────────
#
# Named, so the card can be reasoned about as a whole rather than as scattered
# numbers. X is where every line of text starts; the safe zone is the centre square
# some platforms crop to.
X = 64                 # the text column's left edge
SAFE_L, SAFE_R = 285, 915   # the centre square a 1:1 crop keeps

MARK_SIZE = 62
NAME_SIZE = 44
SUB_SIZE = 23
CLAIM_SIZE = 52
FACT_SIZE = 30

Y_MARK = 84
Y_NAME = 92
Y_SUB = 144
Y_CLAIM = 268
Y_CLAIM_2 = 330
Y_FACTS = 424
FACT_STEP = 46

for path in (WALL, MARK):
    if not os.path.exists(path):
        sys.exit('missing %s' % path)

# The wallpaper is graded, then the plate is applied as a full-height horizontal
# gradient: solid on the left where the text is, clearing to the right where the
# subject is. The first version's plate faded to nothing by x=864 and left the type
# on bare wallpaper - which is why a review said the card "relies entirely on the
# dark void".
grade = (
    f'scale={W}:{H}:force_original_aspect_ratio=increase,'
    f'crop={W}:{H},'
    'eq=brightness=-0.14:contrast=1.12:saturation=0.92,'
    'vignette=PI/4'
)

r = subprocess.run(
    ['ffmpeg', '-v', 'error', '-y', '-i', WALL, '-vf', grade, '-frames:v', '1',
     OUT + '.base.png'],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print('  ffmpeg failed:')
    print('   ', r.stderr.strip()[:500])
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print('  Pillow is needed for the text overlay')
    print('  the graded plate is at %s.base.png' % OUT)
    sys.exit(1)

base = Image.open(OUT + '.base.png').convert('RGB')

# ── the plate ────────────────────────────────────────────────────────────────
#
# A gradient rather than a fading strip. Solid to x=0.62W, then clearing. The
# subject lives right of 0.72W, so it is never covered.
plate = Image.new('RGBA', (W, H), (0, 0, 0, 0))
pd = ImageDraw.Draw(plate)
for x in range(W):
    f = x / float(W)
    if f <= 0.62:
        a = 214
    else:
        # Clear over the last third, smoothly.
        k = (f - 0.62) / 0.38
        a = int(214 * (1 - k) ** 1.25)
    pd.line([(x, 0), (x, H)], fill=(8, 9, 13, a))
base = Image.alpha_composite(base.convert('RGBA'), plate).convert('RGB')

draw = ImageDraw.Draw(base)

FONT_DIR = 'site/assets/fonts'
FONT_CANDIDATES = [
    os.path.join(FONT_DIR, 'jakarta-latin.woff2'),
    'C:/Windows/Fonts/segoeuib.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    'C:/Windows/Fonts/arial.ttf',
]


def load(size):
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ── the mark and the wordmark ────────────────────────────────────────────────
mark = Image.open(MARK).convert('RGBA').resize((MARK_SIZE, MARK_SIZE), Image.LANCZOS)
base.paste(mark, (X, Y_MARK), mark)

f_name = load(NAME_SIZE)
f_sub = load(SUB_SIZE)
f_claim = load(CLAIM_SIZE)
f_fact = load(FACT_SIZE)

draw.text((X + MARK_SIZE + 18, Y_NAME), 'LumaWall', font=f_name, fill=(247, 248, 250))
draw.text((X + MARK_SIZE + 18, Y_SUB), 'Wallpaper hidup untuk Windows',
          font=f_sub, fill=(168, 176, 186))

# ── the claim ────────────────────────────────────────────────────────────────
#
# Two lines, and both start at X. The second line is the brand colour, which is what
# carries the eye from the white line into the benefit.
draw.text((X, Y_CLAIM), 'Wallpaper bergerak,', font=f_claim, fill=(247, 248, 250))
draw.text((X, Y_CLAIM_2), 'komputer tetap tenang', font=f_claim, fill=(255, 74, 100))

# ── the facts ────────────────────────────────────────────────────────────────
#
# Set at FACT_SIZE, which is 30px - readable at 400px wide, where the first version's
# 21px was not. Each fact gets a coloured tick so the three read as a list at a
# glance rather than as three lines of prose.
facts = [
    ('5.000+ wallpaper', (58, 208, 224)),
    ('CPU di bawah 1%', (53, 224, 122)),
    ('Gratis, tanpa iklan', (255, 176, 32)),
]

y = Y_FACTS
for text, colour in facts:
    # The tick: a short bright bar, which reads as a bullet at any size.
    draw.rounded_rectangle([X, y + 8, X + 6, y + 30], radius=3, fill=colour)
    draw.text((X + 22, y), text, font=f_fact, fill=(214, 220, 228))
    y += FACT_STEP

base.save(OUT, 'PNG', optimize=True)
os.remove(OUT + '.base.png')

print('  %s  (%d bytes, %dx%d)' % (OUT, os.path.getsize(OUT), W, H))
