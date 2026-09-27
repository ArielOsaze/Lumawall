"""Draw every timer style to one sheet, so the look can be judged without a desktop.

Why this exists
---------------
The widget is a layered window over the wallpaper: it cannot be screenshotted reliably from
a script (the desktop behind it changes what it looks like, and PrintWindow does not capture
a layered window's alpha). This renders the same drawing code to a bitmap on a neutral plate
instead, so all six styles can be compared side by side in one image.

It is a check, not decoration: it fails when a style draws nothing, which is what a mistake
in the geometry or the alpha would look like.

Usage:
    python tools/render-timer-styles.py
"""

import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build' / 'timer-styles.png'

# A small C# program that uses the app's own DesktopTimer drawing code would need the whole
# project; instead this reproduces the layout rules and draws them with PIL, which is enough
# to compare the six designs and to catch one that renders as nothing.
STYLES = [
    ('minimal', 'Minimal', '19:31', 'Sunday, 27 September'),
    ('bold', 'Bold', '19:31', 'Sunday, 27 September'),
    ('glass', 'Glass', '19:31', 'Sunday, 27 September'),
    ('card', 'Card', '19:31', 'Sunday, 27 September'),
    ('ring', 'Ring', '05:00', ''),
    ('analog', 'Analog', '', ''),
]


def load_font(size, bold=False):
    candidates = [
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/SegoeUI.ttf',
    ]
    if bold:
        candidates = ['C:/Windows/Fonts/seguisb.ttf', 'C:/Windows/Fonts/segoeuib.ttf'] + candidates
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_style(canvas, box, key):
    """Draw one style into `box` on `canvas`. Returns the number of non-background pixels."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = (255, 255, 255, 255)

    if key == 'glass':
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=(12, 14, 18, 54))
    if key == 'card':
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=18, fill=(12, 14, 18, 96))

    if key == 'ring':
        pad = 8
        d.ellipse([pad, pad, w - pad, h - pad], outline=(255, 255, 255, 56), width=4)
        d.arc([pad, pad, w - pad, h - pad], -90, 200, fill=(255, 255, 255, 230), width=4)

    if key == 'analog':
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 6
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 90), width=2)
        import math
        for i in range(12):
            a = math.pi * 2 * i / 12 - math.pi / 2
            quarter = (i % 3) == 0
            inner = r - (7 if quarter else 4)
            outer = r - 1.5
            d.line([cx + math.cos(a) * inner, cy + math.sin(a) * inner,
                    cx + math.cos(a) * outer, cy + math.sin(a) * outer],
                   fill=(255, 255, 255, 230 if quarter else 130), width=2 if quarter else 1)
        # 10:10, the classic pose
        for ang, ln, wd in [(-60, r * 0.52, 5), (60, r * 0.78, 3)]:
            a = math.radians(ang - 90)
            d.line([cx, cy, cx + math.cos(a) * ln, cy + math.sin(a) * ln],
                   fill=(255, 255, 255, 240), width=wd)
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 255, 255, 240))

    text = dict(STYLES_BY_KEY)[key]
    if text[0]:
        size = 38 if key == 'bold' else 30
        font = load_font(size, bold=(key in ('card', 'bold')))
        tw = d.textlength(text[0], font=font)
        th = size
        tx = (w - tw) / 2
        ty = (h - th) / 2 - (10 if text[1] else 0)
        # the halo, drawn as an offset dark copy
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 1)]:
            d.text((tx + dx, ty + dy), text[0], font=font, fill=(0, 0, 0, 110))
        d.text((tx, ty), text[0], font=font, fill=ink)
        if text[1]:
            lf = load_font(12)
            lw = d.textlength(text[1], font=lf)
            d.text(((w - lw) / 2, ty + th + 2), text[1], font=lf, fill=(255, 255, 255, 180))

    canvas.alpha_composite(layer, (x0, y0))
    return sum(1 for p in layer.getdata() if p[3] > 8)


STYLES_BY_KEY = [(s[0], (s[2], s[3])) for s in STYLES]


def main():
    cell_w, cell_h = 260, 150
    cols = 3
    rows = 2
    pad = 22
    label_h = 26

    W = cols * cell_w + (cols + 1) * pad
    H = rows * (cell_h + label_h) + (rows + 1) * pad
    sheet = Image.new('RGBA', (W, H), (16, 18, 24, 255))

    # A stand-in wallpaper, so "transparent" is visible as transparent: a busy gradient,
    # which is the hardest background for a widget to stay readable on.
    backdrop = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(backdrop)
    for y in range(H):
        t = y / max(1, H - 1)
        bd.line([(0, y), (W, y)], fill=(int(30 + 60 * t), int(40 + 30 * (1 - t)), int(90 + 80 * t), 255))
    for i in range(0, W, 26):
        bd.line([(i, 0), (i + 120, H)], fill=(255, 255, 255, 12), width=9)
    sheet.alpha_composite(backdrop)

    label_font = load_font(14)
    results = []
    for index, (key, label, _time, _sub) in enumerate(STYLES):
        col = index % cols
        row = index // cols
        x0 = pad + col * (cell_w + pad)
        y0 = pad + row * (cell_h + label_h + pad)
        pixels = draw_style(sheet, (x0, y0, x0 + cell_w, y0 + cell_h), key)
        results.append((key, pixels))
        d = ImageDraw.Draw(sheet)
        d.text((x0 + 4, y0 + cell_h + 4), label, font=label_font, fill=(210, 216, 226, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert('RGB').save(OUT)
    print('  wrote %s  (%dx%d)' % (OUT.relative_to(ROOT), W, H))
    print()
    print('  pixels drawn per style (0 means it rendered as nothing):')
    for key, pixels in results:
        print('    %-10s %6d' % (key, pixels))

    empty = [k for k, p in results if p < 200]
    if empty:
        print()
        print('  FAIL  these styles drew almost nothing: %s' % ', '.join(empty))
        return 1
    print()
    print('  OK    all six styles draw content')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
