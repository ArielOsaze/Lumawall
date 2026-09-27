"""Draw LumaWall's app icon: one colour, a gaming mark.

Why this exists
---------------
The old mark was an "L" filled with a pink-to-cyan gradient. That is the look the user
singled out - "warna warni kek ai slop" - and it is a fair description: a two-hue neon
gradient on a dark tile is the default output of every icon generator, and it reads as
decoration rather than as a product.

The rule here is one colour. The mark is a single hue on a near-black tile, and the hue is
the app's own crimson (255, 46, 67), so the icon and the window agree. Nothing else is
tinted: no second hue, no gradient, no glow in another colour.

The shape is a viewfinder bracket - four corner marks around a lit centre - which is what a
wallpaper engine does: it frames a screen and puts something moving inside it. Corner
brackets are also a long-standing gaming and HUD convention (targeting reticles, capture
frames, aim-down-sight overlays), which is the impression asked for, and they stay legible
at 16x16 where a detailed mark turns to mush.

Everything is drawn from signed distance fields with 4x supersampling, so the edges are
antialiased at every size and no size needs its own hand-tuned artwork.

Usage:
    python tools/make-icons.py            # draw every asset
    python tools/make-icons.py --check    # report colours, change nothing
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# The app's crimson, from MainWindow.cs: CPrimary = Color.FromRgb(255, 46, 67).
# One colour for the whole mark.
ACCENT = (255, 46, 67)
ACCENT_HI = (255, 96, 116)      # CPrimaryHi, used only for the centre dot's core
TILE = (10, 12, 16)             # CSidebar, the same near-black the app draws its chrome on

# The tile is rounded like the window's own corners.
TILE_RADIUS = 0.20              # fraction of the tile's side


def _rounded_tile(size, radius=TILE_RADIUS, inset=0.0):
    """Coverage of a rounded square, 0..1, at the given resolution.

    `radius` is the corner radius as a fraction of the tile's side. The first version of
    this computed `half * (1 - radius * 2) + half * radius * 2`, which is just `half` -
    every value of radius produced a full circle, and the icon came out round.
    """
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    c = (size - 1) / 2.0
    half = size / 2.0 * (1.0 - inset) - 0.5
    r = half * radius * 2.0
    r = max(0.0, min(r, half))
    # distance to the rounded rectangle's boundary
    dx = np.maximum(np.abs(x - c) - (half - r), 0.0)
    dy = np.maximum(np.abs(y - c) - (half - r), 0.0)
    d = np.sqrt(dx * dx + dy * dy) - r
    inside = np.clip(0.5 - d, 0.0, 1.0)
    # also clip to the square itself
    sq = np.clip(0.5 + (half - np.maximum(np.abs(x - c), np.abs(y - c))), 0.0, 1.0)
    return inside * sq


def _box(px, py, cx, cy, half_w, half_h):
    """Signed distance to an axis-aligned box; negative inside."""
    dx = np.abs(px - cx) - half_w
    dy = np.abs(py - cy) - half_h
    outside = np.sqrt(np.maximum(dx, 0.0) ** 2 + np.maximum(dy, 0.0) ** 2)
    inside = np.minimum(np.maximum(dx, dy), 0.0)
    return outside + inside


def _disc(px, py, cx, cy, r):
    return np.sqrt((px - cx) ** 2 + (py - cy) ** 2) - r


def draw(size, ss=4):
    """The mark at `size` pixels, supersampled `ss` times per axis.

    The mark is four corner brackets and a lit centre, all in one hue. The brackets are
    drawn as the union of two arms each, so a corner is a single solid shape rather than
    two strokes meeting - that is what keeps the corners from thinning where they join.

    Below 32px the ring around the centre is dropped and the centre becomes a solid dot.
    At 16px a 1px ring and a 2px gap between it and the dot do not survive resampling: the
    centre turns into a smudge and the icon reads as a red blob rather than as a frame.
    """
    n = size * ss
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    # normalised coordinates in [-1, 1]
    px = (x + 0.5) / n * 2.0 - 1.0
    py = (y + 0.5) / n * 2.0 - 1.0

    small = size < 32

    # --- geometry, all in the same normalised space -------------------------
    # Brackets sit inside a square frame; the gap in the middle is left open so the mark
    # reads as a frame rather than as a filled box.
    if small:
        arm_len = 0.34      # reach further along each edge, so the corner is unmistakable
        thick = 0.155       # and thicker, so it survives resampling
        edge = 0.60
    else:
        arm_len = 0.30
        thick = 0.115
        edge = 0.62

    mark = np.full((n, n), 1e9)

    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * edge
            cy = sy * edge
            # horizontal arm: runs inward from the corner
            hx = cx - sx * (arm_len / 2.0)
            d1 = _box(px, py, hx, cy, arm_len / 2.0, thick / 2.0)
            # vertical arm
            vy = cy - sy * (arm_len / 2.0)
            d2 = _box(px, py, cx, vy, thick / 2.0, arm_len / 2.0)
            mark = np.minimum(mark, np.minimum(d1, d2))

    # The centre: the "live" part of the frame. A solid dot at small sizes, a ringed one
    # when there is room for the ring to be seen.
    if small:
        centre = _disc(px, py, 0.0, 0.0, 0.19)
    else:
        d_ring = np.abs(_disc(px, py, 0.0, 0.0, 0.30)) - 0.055
        d_core = _disc(px, py, 0.0, 0.0, 0.115)
        centre = np.minimum(d_ring, d_core)

    # --- coverage ----------------------------------------------------------
    def cov(d):
        return np.clip(0.5 - d * (n / 2.0) / 1.0, 0.0, 1.0)

    # distance is in normalised units; convert to pixels for a 1px antialias band
    scale = n / 2.0
    mark_a = np.clip(0.5 - mark * scale, 0.0, 1.0)
    centre_a = np.clip(0.5 - centre * scale, 0.0, 1.0)

    tile_a = _rounded_tile(n)

    # composite: tile, then the mark in one hue, then the core in the lighter shade
    img = np.zeros((n, n, 4), dtype=np.float64)
    for i in range(3):
        img[..., i] = TILE[i]

    # the mark (brackets + ring) in the accent
    for i in range(3):
        img[..., i] = img[..., i] * (1 - mark_a) + ACCENT[i] * mark_a
    # the core, a shade lighter, on top
    for i in range(3):
        img[..., i] = img[..., i] * (1 - centre_a) + ACCENT_HI[i] * centre_a

    img[..., 3] = tile_a * 255.0

    # downsample to the target size - this is the antialiasing
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA')
    return out.resize((size, size), Image.LANCZOS)


def write_ico(path, sizes):
    """Write a multi-size .ico containing PNG-encoded frames."""
    import io
    frames = []
    for s in sizes:
        buf = io.BytesIO()
        draw(s).save(buf, format='PNG')
        frames.append((s, buf.getvalue()))

    header = struct.pack('<HHH', 0, 1, len(frames))
    entries = b''
    offset = 6 + 16 * len(frames)
    body = b''
    for s, data in frames:
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        entries += struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        body += data
    Path(path).write_bytes(header + entries + body)


def report(path):
    """The colours actually present, so 'one colour' can be checked rather than claimed."""
    im = Image.open(path).convert('RGBA')
    im.thumbnail((64, 64))
    a = np.asarray(im).reshape(-1, 4)
    a = a[a[:, 3] > 200]
    if not len(a):
        return []
    q = (a[:, :3] // 32 * 32)
    uniq = {}
    for row in q:
        uniq[tuple(int(v) for v in row)] = uniq.get(tuple(int(v) for v in row), 0) + 1
    return sorted(uniq.items(), key=lambda kv: -kv[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='report colours, change nothing')
    args = ap.parse_args()

    targets = {
        ROOT / 'LumaWall' / 'app.ico': 'ico',
        ROOT / 'site' / 'assets' / 'logo' / 'app.ico': 'ico',
        ROOT / 'site' / 'assets' / 'logo' / 'app-logo.png': 512,
        ROOT / 'site' / 'assets' / 'logo' / 'logo-150.png': 150,
        ROOT / 'site' / 'assets' / 'logo' / 'logo-50.png': 50,
    }

    tile_dir = ROOT / 'LumaWall' / 'TileAssets'
    for name, size in [
        ('Square44x44Logo.png', 44),
        ('Square44x44Logo.altform-unplated.png', 44),
        ('Square44x44Logo.altform-lightunplated.png', 44),
        ('Square71x71Logo.png', 71),
        ('Square150x150Logo.png', 150),
        ('Wide310x150Logo.png', None),        # handled below
        ('StoreLogo.png', 50),
        ('SplashScreen.png', None),
    ]:
        targets[tile_dir / name] = size

    if args.check:
        for path in targets:
            if not Path(path).exists():
                print('  %-52s missing' % Path(path).name)
                continue
            c = report(path)
            head = ', '.join('rgb%s' % (k,) for k, _ in c[:4])
            print('  %-52s %s' % (Path(path).name, head))
        return 0

    for path, size in targets.items():
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if size == 'ico':
            write_ico(path, [16, 24, 32, 48, 64, 128, 256])
        elif size is None:
            continue    # wide and splash need their own aspect; see below
        else:
            draw(size).save(path)
        print('  wrote %s' % path.relative_to(ROOT))

    # Wide tile and splash: the mark centred on the same tile colour, at their own aspect.
    for name, (w, h) in [('Wide310x150Logo.png', (310, 150)),
                         ('SplashScreen.png', (620, 300))]:
        path = tile_dir / name
        mark = draw(min(w, h) * 2 // 3)
        canvas = Image.new('RGBA', (w, h), TILE + (255,))
        canvas.paste(mark, ((w - mark.width) // 2, (h - mark.height) // 2), mark)
        canvas.save(path)
        print('  wrote %s' % path.relative_to(ROOT))

    # Scaled variants of the tile art, which the manifest asks for by name.
    for base in ['Square44x44Logo', 'Square150x150Logo', 'Square71x71Logo']:
        src = tile_dir / (base + '.png')
        if not src.exists():
            continue
        im = Image.open(src)
        for scale in (125, 150, 200, 400):
            out = im.resize((im.width * scale // 100, im.height * scale // 100),
                            Image.LANCZOS)
            out.save(tile_dir / ('%s.scale-%d.png' % (base, scale)))
        print('  wrote %s scale variants' % base)

    for base in ['Square44x44Logo.altform-unplated', 'Square44x44Logo.altform-lightunplated']:
        src = tile_dir / (base + '.png')
        if not src.exists():
            continue
        im = Image.open(src)
        for scale in (125, 150, 200, 400):
            out = im.resize((im.width * scale // 100, im.height * scale // 100),
                            Image.LANCZOS)
            out.save(tile_dir / ('%s.scale-%d.png' % (base, scale)))
        print('  wrote %s scale variants' % base)

    print()
    print('  every asset drawn in one hue: rgb%s' % (ACCENT,))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
