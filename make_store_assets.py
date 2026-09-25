"""
Generates every MSIX / Microsoft Store asset required by the "App icons and
logos" packaging rules, plus the .ico used by the classic installer.

The brand mark is an angular "W" (LumaWall) built from four tapered blades on a
single diagonal crimson -> hot white -> cyan ramp, sitting on a dark squircle
plate with a soft bloom. Everything - taskbar icon, Start tile, Store listing,
splash screen, and the in-app title bar (MainWindow.BuildLogoMark) - is drawn
from this one geometry so the identity cannot drift.

Spec reference (all sizes are the mandatory 100% scale; the 125/150/200/400%
variants are emitted so the package validates and scales cleanly):

  Square44x44Logo       44, 55, 66, 88, 176   (+ _targetsize + _altform-unplated)
  Square150x150Logo    150, 188, 225, 300, 600
  Wide310x150Logo      310x150, 388x188, 465x225, 620x300, 1240x600
  StoreLogo            50, 63, 75, 100, 200
  SplashScreen         620x300, 775x375, 930x450, 1240x600, 2480x1200
  LockScreenLogo       24, 30, 36, 48, 96
  BadgeLogo            24, 30, 36, 48, 96  (monochrome white on transparent)

Store art (not part of the MSIX, uploaded to Partner Center):
  StoreListing_300x300, PosterArt_720x1080, BoxArt_1080x1080, HeroArt_1920x1080
"""
import io
import math
import os
import struct
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work"
APP = os.path.join(ROOT, "LumaWall")
# NOT "Assets": the wallpaper library already owns `LumaWall\assets`, and Windows
# paths are case-insensitive, so an `Assets` folder would be the same directory.
TILE_ASSETS = os.path.join(APP, "TileAssets")
STORE_ART = os.path.join(ROOT, "store-art")

# Brand palette, kept byte-identical to MainWindow.cs
INK_TOP = (16, 19, 26)
INK_BOTTOM = (7, 8, 11)
CRIMSON = (255, 46, 67)
CRIMSON_HI = (255, 96, 116)
CYAN = (34, 211, 238)
WHITE = (242, 245, 250)

SS = 4  # supersample factor for smooth edges

# Fraction of the tile the mark spans. `mark_outline` draws the L across 0.76 of
# whatever span it is given, so these values are chosen to land the final mark at
# the size a launcher icon should be:
#
#   plated  : 0.94 * 0.76 = 0.71 of the tile - the mark fills the plate the way
#             an app icon does, instead of floating in the middle of it. The
#             previous 0.30 padding produced a 53% mark, which read as small and
#             off-centre.
#   bare    : 1.00 * 0.76 = 0.76, slightly larger since there is no plate to
#             frame it (used for the taskbar's unplated variants).
PAD_PLATED = 0.06
PAD_BARE = 0.00


# --------------------------------------------------------------------------
# brand mark: a chamfered "L" (LumaWall)
# --------------------------------------------------------------------------
def _ramp(stops, t):
    """Samples a (position, colour) stop list at t in 0..1."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        t0, c0 = stops[i - 1]
        t1, c1 = stops[i]
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(int(round(c0[k] + (c1[k] - c0[k]) * f)) for k in range(3))
    return stops[-1][1]


_RAMP_STOPS = [
    (0.00, CRIMSON),
    (0.28, CRIMSON_HI),
    (0.50, (255, 238, 244)),
    (0.72, (124, 233, 252)),
    (1.00, CYAN),
]


def _build_ramp_lut(n=512):
    """Pre-samples the brand ramp into a lookup table (fast: no per-pixel calls)."""
    lut = []
    for i in range(n):
        t = i / (n - 1.0)
        c = _ramp(_RAMP_STOPS, t)
        lut.append(c)
    return lut


_RAMP_LUT = _build_ramp_lut()


def mark_gradient(size, size_hint=None):
    """
    Diagonal ramp used to fill the mark: crimson -> hot white -> cyan, i.e. the
    app's own CPrimary/CPrimaryHi/CAccent values, so the icon and the UI agree.

    Below ~24 px the five-stop ramp compresses into mud, so the small sizes get
    the two brand anchors only - a clean crimson-to-cyan sweep instead of a
    smeared three-colour blur.

    Built at a modest resolution and scaled up - a smooth ramp gains nothing
    from extra pixels, and the LUT keeps this fast enough to run per asset.
    """
    n = min(320, max(96, size))
    small = Image.new("RGB", (n, n))
    px = small.load()
    last = len(_RAMP_LUT) - 1
    for y in range(n):
        for x in range(n):
            t = (x + y) / (2.0 * (n - 1))
            if size_hint is not None and size_hint <= 24:
                # Straight crimson -> cyan; the white midpoint is dropped.
                px[x, y] = _ramp([(0.0, CRIMSON), (1.0, CYAN)], t)
            else:
                px[x, y] = _RAMP_LUT[int(t * last + 0.5)]
    return small.resize((size, size), Image.BILINEAR)


def mark_outline(cx, cy, span, size_hint=None):
    """
    The brand mark: a bold "L" with 45-degree chamfers on its two outer corners
    and a sharp inner corner.

    "L" for LumaWall. The chamfers give it the angular, engineered feel the rest
    of the UI has, and the letter stays legible down to 16 px because the strokes
    are thick and the silhouette is simple.

    Coordinates are relative to the mark's own box (-0.5..0.5) scaled by `span`,
    so the same numbers drive the .ico, the Store tiles and the in-app title bar.

    `size_hint` is the on-screen pixel size the artwork is destined for. Below
    ~20 px the chamfers and the gradient both fall below one pixel, so the strokes
    are thickened and the chamfers shrunk to keep the L readable - standard
    optical sizing, where the drawing adapts rather than being scaled blindly.
    """
    def pt(x, y):
        return (cx + x * span, cy + y * span)

    # Defaults are the large-size drawing.
    stroke = 0.30        # vertical stroke width, and the arm height
    chamfer = 0.14       # 45-degree cut on the two outer corners
    if size_hint is not None and size_hint <= 20:
        stroke = 0.36    # thicker: a 0.30 stroke lands on ~1 px at 16 px
        chamfer = 0.10   # smaller: the cut was eating the whole corner
    elif size_hint is not None and size_hint <= 28:
        stroke = 0.33
        chamfer = 0.12

    x0, x1 = -0.38, 0.38          # mark box
    y0, y1 = -0.38, 0.38
    inner_x = x0 + stroke         # inner corner, x
    inner_y = y1 - stroke         # inner corner, y

    return [
        pt(x0 + chamfer, y0),     # top-left, after the 45-degree chamfer
        pt(inner_x, y0),          # top of the vertical stroke
        pt(inner_x, inner_y),     # inner corner (kept sharp so the L reads as an L)
        pt(x1, inner_y),          # top of the foot
        pt(x1, y1 - chamfer),     # right edge
        pt(x1 - chamfer, y1),     # bottom-right, after the chamfer
        pt(x0, y1),               # bottom-left
        pt(x0, y0 + chamfer),     # left edge
    ]


def composite_mark(img, size, cx, cy, span, monochrome=None, size_hint=None):
    """
    Paints the mark onto `img`. Gradient by default, flat white for the Store
    badge (which must be monochrome).

    `size_hint` drives the optical sizing; see mark_outline.
    """
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(mark_outline(cx, cy, span, size_hint), fill=255)

    if monochrome is not None:
        fill = Image.new("RGBA", (size, size), tuple(monochrome) + (255,))
    else:
        fill = mark_gradient(size, size_hint)
    img.paste(fill, (0, 0), mask)
    return img


# --------------------------------------------------------------------------
# tiles
# --------------------------------------------------------------------------
def squircle_mask(size, radius_ratio=0.235):
    m = Image.new("L", (size * SS, size * SS), 0)
    d = ImageDraw.Draw(m)
    r = int(size * SS * radius_ratio)
    d.rounded_rectangle([0, 0, size * SS - 1, size * SS - 1], radius=r, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def vertical_gradient(size, top, bottom):
    g = Image.new("RGB", (1, size * SS))
    for y in range(size * SS):
        t = y / max(1, size * SS - 1)
        g.putpixel((0, y), (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        ))
    return g.resize((size * SS, size * SS), Image.NEAREST)


def brand_square(size, transparent=False, pad_ratio=PAD_PLATED):
    """Square brand tile. transparent=True leaves the plate off (logo only)."""
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if not transparent:
        plate = vertical_gradient(size, INK_TOP, INK_BOTTOM).convert("RGBA")
        # Bloom sits behind the mark, so it has to stay clear of it. The mark now
        # spans 71% of the tile (it used to be 53%), and a strong bloom under the
        # larger mark bled through the gradient and made the inner corner look
        # smudged. Keep it subtle and pushed to the edges.
        bloom = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bloom)
        bd.ellipse([-S * 0.35, -S * 0.45, S * 0.55, S * 0.45], fill=CRIMSON + (44,))
        bd.ellipse([S * 0.55, S * 0.50, S * 1.35, S * 1.30], fill=CYAN + (28,))
        bloom = bloom.filter(ImageFilter.GaussianBlur(S * 0.11))
        img = Image.alpha_composite(img, plate)
        img = Image.alpha_composite(img, bloom)

        rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        r = int(size * SS * 0.235)
        rd.rounded_rectangle([1, 1, S - 2, S - 2], radius=r - 1,
                             outline=(255, 255, 255, 34), width=max(1, int(SS * 0.9)))
        img = Image.alpha_composite(img, rim)

    composite_mark(img, S, S / 2.0, S / 2.0, S * (1.0 - pad_ratio), size_hint=size)

    img = img.resize((size, size), Image.LANCZOS)
    if not transparent:
        img.putalpha(squircle_mask(size))
    return img


def brand_wide(width, height):
    """Wide tile: plate fills the frame, mark sits on the left third."""
    S = SS
    W, H = width * S, height * S
    img = vertical_gradient(height, INK_TOP, INK_BOTTOM).resize((W, H), Image.NEAREST).convert("RGBA")
    bloom = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    bd.ellipse([-W * 0.15, -H * 0.6, W * 0.55, H * 0.9], fill=CRIMSON + (52,))
    bd.ellipse([W * 0.55, -H * 0.3, W * 1.25, H * 1.4], fill=CYAN + (30,))
    bloom = bloom.filter(ImageFilter.GaussianBlur(W * 0.045))
    img = Image.alpha_composite(img, bloom)

    composite_mark(img, W, H * 0.36, H * 0.5, H * 0.62)

    img = img.resize((width, height), Image.LANCZOS)
    return img


def brand_badge(size):
    """Monochrome badge: white mark on transparent (Store requirement)."""
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    composite_mark(img, S, S / 2.0, S / 2.0, S * 0.80, monochrome=(255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------------------------
# writers
# --------------------------------------------------------------------------
SCALES = [(100, 1.0), (125, 1.25), (150, 1.5), (200, 2.0), (400, 4.0)]


def write_png(img, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path, "PNG")
    return path


def verify_asset_folder():
    """
    Guards against the trap that made an earlier package fail certification:
    Windows paths are case-insensitive, so a folder named `Assets` and one named
    `assets` in the same directory are the SAME folder. The wallpaper library
    already uses `assets`, so if the tile art is generated into a sibling
    `Assets` folder the two collide and the manifest's `Assets\\...` references
    resolve to library files instead of logos.

    The tile art therefore lives in `TileAssets`, and this check asserts the two
    folders are genuinely distinct before anything is written.
    """
    lib = os.path.join(APP, "assets")
    tiles = TILE_ASSETS
    if os.path.normcase(os.path.abspath(lib)) == os.path.normcase(os.path.abspath(tiles)):
        raise SystemExit("FATAL: tile asset folder collides with the wallpaper library folder")
    os.makedirs(tiles, exist_ok=True)
    return tiles


def write_square_set(base_name, base_size, transparent=False):
    """Square44x44Logo / Square150x150Logo / StoreLogo: scaled variants."""
    made = []
    for (pct, factor) in SCALES:
        px = int(round(base_size * factor))
        img = brand_square(px, transparent=transparent,
                           pad_ratio=PAD_BARE if transparent else PAD_PLATED)
        suffix = "" if pct == 100 else ".scale-%d" % pct
        made.append(write_png(img, os.path.join(TILE_ASSETS, "%s%s.png" % (base_name, suffix))))
    return made


def write_square_targetsize(base_name, base_size):
    """Target-size variants used by the taskbar / Start tiles."""
    made = []
    for px in sorted({int(round(base_size * f)) for (_, f) in SCALES} | {16, 24, 32, 48, 256}):
        img = brand_square(px, transparent=True, pad_ratio=PAD_BARE)
        made.append(write_png(img, os.path.join(TILE_ASSETS, "%s.targetsize-%d.png" % (base_name, px))))
    return made


def write_wide_set(base_name, base_w, base_h):
    made = []
    for (pct, factor) in SCALES:
        w = int(round(base_w * factor))
        h = int(round(base_h * factor))
        suffix = "" if pct == 100 else ".scale-%d" % pct
        made.append(write_png(brand_wide(w, h), os.path.join(TILE_ASSETS, "%s%s.png" % (base_name, suffix))))
    return made


def write_badge_set(base_name, base_size):
    made = []
    for (pct, factor) in SCALES:
        px = int(round(base_size * factor))
        suffix = "" if pct == 100 else ".scale-%d" % pct
        made.append(write_png(brand_badge(px), os.path.join(TILE_ASSETS, "%s%s.png" % (base_name, suffix))))
    return made


def write_ico(master, path):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    pngs = []
    for s in sizes:
        buf = io.BytesIO()
        master.resize((s, s), Image.LANCZOS).save(buf, format="PNG")
        pngs.append((s, buf.getvalue()))
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, body = b"", b""
    for (s, data) in pngs:
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    with open(path, "wb") as fh:
        fh.write(header + entries + body)
    return path


# --------------------------------------------------------------------------
# store listing art (uploaded to Partner Center, not packaged)
# --------------------------------------------------------------------------
def listing_tile(width, height, title=None):
    """Polished marketing tile: dark plate, brand mark, optional wordmark."""
    S = 2
    W, H = width * S, height * S
    img = vertical_gradient(height, (18, 21, 30), (6, 7, 10)).resize((W, H), Image.NEAREST).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-W * 0.25, -H * 0.55, W * 0.6, H * 0.85], fill=CRIMSON + (58,))
    gd.ellipse([W * 0.5, H * 0.2, W * 1.3, H * 1.4], fill=CYAN + (36,))
    glow = glow.filter(ImageFilter.GaussianBlur(W * 0.06))
    img = Image.alpha_composite(img, glow)

    if title:
        composite_mark(img, W, W * 0.5, H * 0.40, H * 0.40)
    else:
        composite_mark(img, W, W * 0.5, H * 0.5, min(W, H) * 0.58)

    img = img.resize((width, height), Image.LANCZOS)
    return img


def main():
    verify_asset_folder()
    os.makedirs(STORE_ART, exist_ok=True)

    # --- MSIX packaged assets ------------------------------------------
    write_square_set("Square44x44Logo", 44, transparent=True)
    write_square_targetsize("Square44x44Logo", 44)
    write_png(brand_square(44, transparent=True, pad_ratio=PAD_BARE),
              os.path.join(TILE_ASSETS, "Square44x44Logo.altform-unplated.png"))
    write_png(brand_square(44, transparent=True, pad_ratio=PAD_BARE),
              os.path.join(TILE_ASSETS, "Square44x44Logo.altform-lightunplated.png"))

    write_square_set("Square150x150Logo", 150)
    write_square_set("StoreLogo", 50)

    write_wide_set("Wide310x150Logo", 310, 150)
    write_wide_set("SplashScreen", 620, 300)

    write_badge_set("LockScreenLogo", 24)
    write_badge_set("BadgeLogo", 24)

    # --- classic .ico for the EXE + Inno installer ---------------------
    master512 = brand_square(512)
    master512.save(os.path.join(APP, "app-logo.png"), "PNG")
    write_ico(master512, os.path.join(APP, "app.ico"))
    # MSIX wants a plain png copy for the tile/Store logo sources
    master512.save(os.path.join(TILE_ASSETS, "AppLogo.png"), "PNG")

    # --- Partner Center marketing art ---------------------------------
    listing_tile(300, 300).save(os.path.join(STORE_ART, "StoreListing_300x300.png"), "PNG")
    listing_tile(1080, 1080).save(os.path.join(STORE_ART, "BoxArt_1080x1080.png"), "PNG")
    listing_tile(720, 1080).save(os.path.join(STORE_ART, "PosterArt_720x1080.png"), "PNG")
    listing_tile(1920, 1080).save(os.path.join(STORE_ART, "HeroArt_1920x1080.png"), "PNG")

    count = len([f for f in os.listdir(TILE_ASSETS) if f.lower().endswith(".png")])
    print("Assets written:", count)
    print("Store art written to:", STORE_ART)


if __name__ == "__main__":
    main()
