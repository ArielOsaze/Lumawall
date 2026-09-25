"""SUPERSEDED - do not use. The promo is now built from React source.

  The current pipeline is:

      cd promo && node render.mjs --duration 52 --crf 19           --out ../site/assets/video/lumawall-promo.mp4

  See promo/README or docs/DESIGN-NOTES.md.

  Why this file is still here: it is the reference for the original frame-by-frame
  approach, and it documents the fonts and layout the promo used before the
  redesign. Running it produces a video that does NOT match the site: Bahnschrift
  and Cascadia Mono instead of Plus Jakarta Sans, static screenshots instead of
  moving wallpapers, and no camera move.

  ---------------------------------------------------------------------------

  Renders the LumaWall promo video frame by frame, then encodes it with ffmpeg.

  Why frames instead of ffmpeg filter graphs: the video needs real typography,
  eased motion, and a Ken Burns treatment of the actual application screenshots.
  Expressing that as a chain of zoompan / drawtext filters is fragile - a single
  escaping mistake silently produces a black frame - whereas drawing each frame
  directly gives exact control and lets the whole thing be verified by inspecting
  individual frames.

  Output: site/assets/video/lumawall-promo.mp4 (1920x1080, 30 fps, H.264)
  """

import math
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SHOTS = os.path.join(SITE, "assets", "shots")
OUT_DIR = os.path.join(SITE, "assets", "video")
FRAME_DIR = os.path.join(ROOT, "build", "promo-frames")

# Brand palette, identical to the site and the app.
BG = (8, 9, 12)
BG_ALT = (12, 14, 19)
PANEL = (17, 20, 27)
ACCENT = (255, 59, 87)
ACCENT_DIM = (201, 37, 63)
CYAN = (53, 214, 232)
GREEN = (53, 224, 122)
TEXT = (238, 241, 246)
MUTED = (152, 161, 178)
DIM = (107, 116, 132)
LINE = (35, 40, 51)

FONT_DIR = r"C:\Windows\Fonts"
F_DISPLAY = os.path.join(FONT_DIR, "bahnschrift.ttf")
F_BOLD = os.path.join(FONT_DIR, "segoeuib.ttf")
F_BODY = os.path.join(FONT_DIR, "segoeui.ttf")
F_MONO = os.path.join(FONT_DIR, "consola.ttf")
F_MONO_B = os.path.join(FONT_DIR, "consolab.ttf")

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ───────────────────────────── easing ─────────────────────────────
def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease_out(t):
    """Decelerating curve - the default for entrances."""
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t, s=1.7):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def span(t, start, end):
    """Normalised progress of a sub-animation inside a scene."""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp((t - start) / (end - start))


# Scenes dissolve into one another, so a scene's first element must already be
# on screen when the scene starts. Fading it in from nothing (the obvious
# choice) makes the crossfade blend two nearly-empty frames, which showed up as
# a black flash at every scene boundary.
FLOOR = 0.45


def enter(t, start, end, floor=FLOOR):
    """Entrance alpha that begins at `floor` instead of zero."""
    return floor + (1.0 - floor) * ease_out(span(t, start, end))


# ───────────────────────────── drawing helpers ─────────────────────────────
def gradient_bg(accent_xy=(0.22, 0.10), accent_col=ACCENT, alpha=0.20):
    """Dark base with a soft brand-coloured radial glow."""
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = accent_xy[0] * W, accent_xy[1] * H
    steps = 90
    for i in range(steps, 0, -1):
        r = int(max(W, H) * 0.95 * i / steps)
        a = (1 - i / steps) ** 2 * alpha
        col = tuple(int(c * a) for c in accent_col)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    return Image.blend(img, Image.blend(img, glow, 0.85), 1.0)


def add_glow_layer(base, accent_xy, accent_col, alpha=0.18):
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = accent_xy[0] * W, accent_xy[1] * H
    steps = 80
    for i in range(steps, 0, -1):
        r = int(max(W, H) * 0.9 * i / steps)
        a = (1 - i / steps) ** 2 * alpha
        col = tuple(int(c * a) for c in accent_col)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(100))
    return Image.blend(base, Image.blend(base, glow, 0.8), 1.0)


def text(draw, xy, s, f, fill, anchor="la", spacing=0):
    xy = (int(round(xy[0])), int(round(xy[1])))
    if spacing == 0:
        draw.text(xy, s, font=f, fill=fill, anchor=anchor)
        return
    # Manual letter spacing for kickers / labels.
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill, anchor=anchor)
        w = draw.textlength(ch, font=f)
        x += w + spacing


def text_w(draw, s, f, spacing=0):
    if spacing == 0:
        return draw.textlength(s, font=f)
    return sum(draw.textlength(c, font=f) for c in s) + spacing * max(0, len(s) - 1)


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


_vignette_mask_cache = {}


def vignette(img, strength=0.55):
    """Darkens the frame edges.

    The mask is identical for every frame of the video, but building it costs a
    full 1920x1080 L image plus a Gaussian blur with a 220 px radius. Doing that
    per frame allocated tens of gigabytes across the render and ended in a
    MemoryError, so the mask is built once and reused.
    """
    mask = _vignette_mask_cache.get(strength)
    if mask is None:
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([-W * 0.25, -H * 0.35, W * 1.25, H * 1.35], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(220))
        _vignette_mask_cache[strength] = mask

    dark = Image.new("RGB", (W, H), (0, 0, 0))
    out = Image.composite(img, dark, mask)
    dark = None
    return Image.blend(img, out, strength)


def ken_burns(src, t, zoom_from=1.0, zoom_to=1.10, pan=(0.0, 0.0), target=(1400, 788)):
    """Slow zoom/pan over a screenshot - keeps a static image alive."""
    tw, th = target
    img = src.copy()
    z = zoom_from + (zoom_to - zoom_from) * ease_in_out(t)
    crop_w = int(img.width / z)
    crop_h = int(img.height / z)
    max_x = img.width - crop_w
    max_y = img.height - crop_h
    x = int(max_x * (0.5 + pan[0] * (t - 0.5)))
    y = int(max_y * (0.5 + pan[1] * (t - 0.5)))
    img = img.crop((x, y, x + crop_w, y + crop_h))
    return img.resize((int(tw), int(th)), Image.LANCZOS)


def place_card(base, img, box, radius=18, shadow=True, border=LINE, border_w=1):
    """Draws an image as a rounded card with a soft shadow."""
    x, y, w, h = (int(round(v)) for v in box)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    inner = img.convert("RGB").resize((w, h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    card.paste(inner, (0, 0), mask)

    base_rgba = base if base.mode == "RGBA" else base.convert("RGBA")

    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [x + 5, y + 16, x + w + 5, y + h + 16], radius=radius, fill=(0, 0, 0, 150))
        base_rgba.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))

    base_rgba.alpha_composite(card, (x, y))

    if border_w:
        od = ImageDraw.Draw(base_rgba)
        od.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=radius, outline=border + (255,), width=border_w)
    return base_rgba


def logo_mark(size, glow=True):
    """The LumaWall mark: squircle plate, crimson-to-cyan gradient, bold L."""
    from PIL import ImageDraw as D
    pad = int(size * 0.10)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pd = D.Draw(plate)
    pd.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1],
                         radius=int(size * 0.22), fill=(18, 21, 28, 255))
    pd.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1],
                         radius=int(size * 0.22), outline=ACCENT + (255,), width=max(2, int(size * 0.012)))
    img.alpha_composite(plate)

    # The letter L, drawn as a chevron-notched stroke like the app icon.
    m = int(size * 0.30)
    inner = size - 2 * m
    stroke = max(3, int(size * 0.115))
    glyph = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = D.Draw(glyph)
    x0, y0 = m, m
    x1, y1 = size - m, size - m
    # vertical bar
    gd.rectangle([x0, y0, x0 + stroke, y1], fill=(255, 255, 255, 255))
    # horizontal bar
    gd.rectangle([x0, y1 - stroke, x1, y1], fill=(255, 255, 255, 255))
    # gradient fill: crimson (top) to cyan (bottom)
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd2 = D.Draw(grad)
    for yy in range(size):
        f = yy / max(1, size - 1)
        col = (int(ACCENT[0] * (1 - f) + CYAN[0] * f),
               int(ACCENT[1] * (1 - f) + CYAN[1] * f),
               int(ACCENT[2] * (1 - f) + CYAN[2] * f), 255)
        gd2.line([(0, yy), (size, yy)], fill=col)
    glyph = Image.composite(grad, Image.new("RGBA", (size, size), (0, 0, 0, 0)), glyph.split()[3])
    img.alpha_composite(glyph)

    if glow:
        g = img.filter(ImageFilter.GaussianBlur(size * 0.09))
        out = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        out.alpha_composite(g, (size // 2, size // 2))
        out.alpha_composite(img, (size // 2, size // 2))
        return out
    return img


def paste_center(base, img, cx, cy, alpha=1.0):
    if alpha <= 0:
        return base
    if alpha < 1:
        img = img.copy()
        a = img.split()[3].point(lambda v: int(v * alpha))
        img.putalpha(a)
    base.alpha_composite(img, (int(round(cx - img.width / 2)), int(round(cy - img.height / 2))))
    return base


# ───────────────────────────── scenes ─────────────────────────────
def scene_intro(t):
    """Logo reveal with the product name."""
    img = gradient_bg((0.5, 0.42), ACCENT, 0.26).convert("RGBA")

    logo_p = ease_out_back(span(t, 0.02, 0.34))
    logo_a = ease_out(span(t, 0.02, 0.26))
    if logo_a > 0:
        size = int(210 * (0.82 + 0.18 * logo_p))
        mark = logo_mark(size, glow=True)
        paste_center(img, mark, W / 2, H / 2 - 118, logo_a)

    name_a = enter(t, 0.22, 0.52)
    if name_a > 0:
        d = ImageDraw.Draw(img)
        f = font(F_DISPLAY, 96)
        s = "LumaWall"
        w = text_w(d, s, f, spacing=2)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        text(ld, (W / 2 - w / 2, H / 2 + 18), s, f, TEXT + (255,), spacing=2)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * name_a)))
        img.alpha_composite(layer)

    tag_a = enter(t, 0.40, 0.68)
    if tag_a > 0:
        d = ImageDraw.Draw(img)
        f = font(F_MONO, 25)
        s = "LIVE WALLPAPER ENGINE"
        w = text_w(d, s, f, spacing=8)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        text(ld, (W / 2 - w / 2, H / 2 + 140), s, f, ACCENT + (255,), spacing=8)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * tag_a)))
        img.alpha_composite(layer)

    return img


def scene_problem(t):
    """Before/after: the CPU cost of software decode vs GPU decode."""
    img = gradient_bg((0.5, 0.0), ACCENT, 0.16).convert("RGBA")
    d = ImageDraw.Draw(img)

    head_a = enter(t, 0.0, 0.22)
    if head_a > 0:
        f = font(F_DISPLAY, 62)
        s = "Wallpaper video biasanya makan CPU"
        w = text_w(d, s, f)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (W / 2 - w / 2, 96), s, f, TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * head_a)))
        img.alpha_composite(layer)

    # Two panels: before (red, high) and after (green, low)
    pw, ph = 760, 420
    gap = 90
    y = 300
    x1 = W / 2 - gap / 2 - pw
    x2 = W / 2 + gap / 2

    left_a = enter(t, 0.14, 0.42)
    right_a = enter(t, 0.30, 0.60)

    def panel(x, label, value, value_col, pct, a, note):
        if a <= 0:
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        rounded(ld, [x, y, x + pw, y + ph], 20, fill=PANEL + (255,), outline=LINE + (255,), width=2)
        text(ld, (x + 44, y + 40), label, font(F_MONO, 22), DIM + (255,), spacing=3)
        text(ld, (x + 44, y + 92), value, font(F_DISPLAY, 104), value_col + (255,))

        # bar
        bx, by, bw, bh = x + 44, y + 240, pw - 88, 52
        rounded(ld, [bx, by, bx + bw, by + bh], 10, fill=(30, 34, 43, 255))
        fill_w = int(bw * pct * ease_out(span(t, 0.34 if pct > 0.5 else 0.50, 0.86)))
        if fill_w > 6:
            rounded(ld, [bx, by, bx + fill_w, by + bh], 10, fill=value_col + (255,))
        text(ld, (x + 44, y + ph - 74), note, font(F_BODY, 24), MUTED + (255,))

        layer.putalpha(layer.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(layer)

    panel(x1, "SEBELUM", "168%", ACCENT, 0.92, left_a, "Software decode, semua di CPU")
    panel(x2, "DENGAN LUMAWALL", "< 1%", GREEN, 0.04, right_a, "Hardware decode di GPU")

    arrow_a = ease_out(span(t, 0.52, 0.74))
    if arrow_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        cx, cy = W / 2, y + ph / 2
        ld.polygon([(cx - 20, cy - 26), (cx + 24, cy), (cx - 20, cy + 26)], fill=CYAN + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * arrow_a)))
        img.alpha_composite(layer)

    return img


def scene_ui(t, shot, kicker, title, sub, pan=(0.0, 0.0)):
    """Screenshot sliding in as a card, with a heading above it."""
    img = gradient_bg((0.5, 0.05), ACCENT, 0.14).convert("RGBA")
    d = ImageDraw.Draw(img)

    ka = enter(t, 0.0, 0.20)
    ta = enter(t, 0.06, 0.32)
    sa = ease_out(span(t, 0.16, 0.42))

    if ka > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        text(ld, (120, 92), kicker, font(F_MONO, 21), ACCENT + (255,), spacing=5)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ka)))
        img.alpha_composite(layer)

    if ta > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 132), title, font(F_DISPLAY, 58), TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ta)))
        img.alpha_composite(layer)

    if sa > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 212), sub, font(F_BODY, 26), MUTED + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * sa)))
        img.alpha_composite(layer)

    # Screenshot card. The card must fit entirely inside the frame: the header
    # occupies the top ~250 px and a bottom margin keeps it off the edge, so the
    # available box is measured first and the card is scaled to fit inside it
    # rather than being cropped by the frame.
    card_a = enter(t, 0.20, 0.55)
    if card_a > 0:
        TOP = 268
        BOTTOM_MARGIN = 54
        avail_h = H - TOP - BOTTOM_MARGIN
        avail_w = W - 240

        scale = min(avail_w / shot.width, avail_h / shot.height)
        target_w = int(shot.width * scale)
        target_h = int(shot.height * scale)

        card = ken_burns(shot, t, 1.0, 1.06, pan, (target_w, target_h))
        cx = W / 2
        # Entrance: fade + a short rise, never enough to leave the frame.
        rise = (1 - ease_out(span(t, 0.20, 0.58))) * 40
        cy = TOP + rise
        img = place_card(img, card, (cx - target_w / 2, cy, target_w, target_h), radius=16)

    return img


def scene_monitors(t):
    """Multi-monitor: one wallpaper per screen, different on each."""
    img = gradient_bg((0.5, 0.02), CYAN, 0.13).convert("RGBA")
    d = ImageDraw.Draw(img)

    ka = enter(t, 0.0, 0.18)
    ta = enter(t, 0.05, 0.28)
    if ka > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 92), "MULTI-MONITOR", font(F_MONO, 21), CYAN + (255,), spacing=5)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ka)))
        img.alpha_composite(layer)
    if ta > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 132), "Beda wallpaper di tiap layar", font(F_DISPLAY, 58), TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ta)))
        img.alpha_composite(layer)

    # Three monitor panels, each revealing in turn with a different tint.
    mw, mh = 500, 300
    gap = 46
    total = mw * 3 + gap * 2
    x0 = (W - total) / 2
    y = 420
    labels = [("MONITOR 1", ACCENT), ("MONITOR 2", CYAN), ("MONITOR 3", (168, 120, 255))]
    for i in range(3):
        a = enter(t, 0.18 + i * 0.12, 0.46 + i * 0.12)
        if a <= 0:
            continue
        x = x0 + i * (mw + gap)
        rise = (1 - a) * 46
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        yy = y + rise
        rounded(ld, [x, yy, x + mw, yy + mh], 16, fill=(15, 18, 24, 255), outline=labels[i][1] + (120,), width=2)
        # animated inner stripes to suggest video
        for k in range(9):
            ph = (t * 2.2 + i * 0.33 + k * 0.11) % 1.0
            ly = yy + 26 + ph * (mh - 52)
            lw = mw - 52
            alpha = int(70 * (1 - abs(ph - 0.5) * 1.4))
            if alpha > 0:
                ld.rectangle([x + 26, ly, x + 26 + lw, ly + 12],
                             fill=labels[i][1] + (max(0, alpha),))
        text(ld, (x + 26, yy + mh - 46), labels[i][0], font(F_MONO, 19), labels[i][1] + (255,), spacing=3)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(layer)

    note_a = ease_out(span(t, 0.62, 0.84))
    if note_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        s = "Simpan sebagai profil — pulihkan dengan satu klik"
        f = font(F_BODY, 28)
        w = text_w(ld, s, f)
        text(ld, (W / 2 - w / 2, 800), s, f, MUTED + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * note_a)))
        img.alpha_composite(layer)

    return img


def scene_pause(t):
    """Fullscreen game -> wallpaper pauses -> instant resume."""
    img = gradient_bg((0.5, 0.02), ACCENT, 0.15).convert("RGBA")
    d = ImageDraw.Draw(img)

    ka = enter(t, 0.0, 0.18)
    ta = enter(t, 0.05, 0.28)
    if ka > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 92), "PAUSE PER-MONITOR", font(F_MONO, 21), ACCENT + (255,), spacing=5)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ka)))
        img.alpha_composite(layer)
    if ta > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(layer), (120, 132), "Game fullscreen? Otomatis berhenti", font(F_DISPLAY, 56), TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * ta)))
        img.alpha_composite(layer)

    # Timeline: OPEN -> PAUSED -> RESUME
    ty = 560
    tw = 1240
    tx = (W - tw) / 2
    line_a = enter(t, 0.16, 0.40)
    if line_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rectangle([tx, ty - 2, tx + int(tw * line_a), ty + 2], fill=LINE + (255,))

        # three markers
        marks = [
            (0.0, "FULLSCREEN DIBUKA", ACCENT),
            (0.5, "PAUSED", (240, 190, 60)),
            (1.0, "RESUME", GREEN),
        ]
        for frac, label, col in marks:
            mx = tx + tw * frac
            ma = ease_out(span(t, 0.22 + frac * 0.22, 0.44 + frac * 0.22))
            if ma <= 0:
                continue
            r = 13
            ld.ellipse([mx - r, ty - r, mx + r, ty + r], fill=col + (255,))
            f = font(F_MONO, 20)
            w = text_w(ld, label, f, spacing=3)
            text(ld, (mx - w / 2, ty + 40), label, f, col + (255,), spacing=3)

        # latency badge
        la = ease_out(span(t, 0.66, 0.86))
        if la > 0:
            f = font(F_DISPLAY, 46)
            s = "4 ms"
            w = text_w(ld, s, f)
            text(ld, (W / 2 - w / 2, ty + 120), s, f, GREEN + (255,))
            f2 = font(F_BODY, 24)
            s2 = "respons — jauh sebelum kamu sadar"
            w2 = text_w(ld, s2, f2)
            text(ld, (W / 2 - w2 / 2, ty + 184), s2, f2, MUTED + (255,))

        layer.putalpha(layer.split()[3].point(lambda v: int(v * line_a)))
        img.alpha_composite(layer)

    return img


def scene_features(t):
    """Feature montage - four points in a 2x2 grid."""
    img = gradient_bg((0.5, 0.0), ACCENT, 0.14).convert("RGBA")

    head_a = enter(t, 0.0, 0.20)
    if head_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        f = font(F_DISPLAY, 56)
        s = "Semua yang kamu butuhkan"
        w = text_w(ld, s, f)
        text(ld, (W / 2 - w / 2, 96), s, f, TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * head_a)))
        img.alpha_composite(layer)

    items = [
        ("Katalog 5.000+", "Cari karakter atau suasana, unduh langsung", ACCENT),
        ("Empat bahasa", "Indonesia, English, 中文, 日本語", CYAN),
        ("Hemat RAM", "Wallpaper statis tanpa WebView — hemat 130 MB/layar", (168, 120, 255)),
        ("Pulih sendiri", "Explorer restart? Wallpaper dipasang ulang otomatis", GREEN),
    ]
    bw, bh = 760, 210
    gap = 44
    x0 = (W - (bw * 2 + gap)) / 2
    y0 = 300
    for i, (title, sub, col) in enumerate(items):
        row, cidx = divmod(i, 2)
        a = enter(t, 0.16 + i * 0.10, 0.44 + i * 0.10)
        if a <= 0:
            continue
        x = x0 + cidx * (bw + gap)
        y = y0 + row * (bh + gap)
        rise = (1 - a) * 34
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        yy = y + rise
        rounded(ld, [x, yy, x + bw, yy + bh], 16, fill=PANEL + (255,), outline=LINE + (255,), width=2)
        ld.rounded_rectangle([x, yy, x + 6, yy + bh], radius=3, fill=col + (255,))
        text(ld, (x + 40, yy + 42), title, font(F_DISPLAY, 36), TEXT + (255,))
        text(ld, (x + 40, yy + 104), sub, font(F_BODY, 23), MUTED + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(layer)

    return img


def scene_outro(t):
    """Download call to action."""
    img = gradient_bg((0.5, 0.38), ACCENT, 0.28).convert("RGBA")

    logo_a = ease_out_back(span(t, 0.02, 0.28))
    if logo_a > 0:
        size = int(180 * (0.86 + 0.14 * logo_a))
        mark = logo_mark(size, glow=True)
        paste_center(img, mark, W / 2, H / 2 - 210, enter(t, 0.02, 0.22))

    a1 = enter(t, 0.18, 0.44)
    if a1 > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        f = font(F_DISPLAY, 76)
        s = "Gratis. Tanpa iklan."
        w = text_w(ld, s, f)
        text(ld, (W / 2 - w / 2, H / 2 - 60), s, f, TEXT + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a1)))
        img.alpha_composite(layer)

    a2 = enter(t, 0.30, 0.56)
    if a2 > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        f = font(F_BODY, 30)
        s = "Windows 10 / 11  ·  x64  ·  versi 4.0.1"
        w = text_w(ld, s, f)
        text(ld, (W / 2 - w / 2, H / 2 + 42), s, f, MUTED + (255,))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a2)))
        img.alpha_composite(layer)

    a3 = enter(t, 0.44, 0.72)
    if a3 > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        bw, bh = 420, 84
        bx, by = W / 2 - bw / 2, H / 2 + 118
        # pulse the button slightly
        pulse = 1.0 + 0.02 * math.sin(t * 14)
        bw2, bh2 = bw * pulse, bh * pulse
        bx2, by2 = W / 2 - bw2 / 2, by + (bh - bh2) / 2
        rounded(ld, [bx2, by2, bx2 + bw2, by2 + bh2], 12, fill=ACCENT + (255,))
        f = font(F_DISPLAY, 32)
        s = "Unduh Sekarang"
        w = text_w(ld, s, f)
        text(ld, (W / 2 - w / 2, by2 + bh2 / 2 - 22), s, f, (255, 255, 255, 255))
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a3)))
        img.alpha_composite(layer)

    a4 = ease_out(span(t, 0.60, 0.86))
    if a4 > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        f = font(F_MONO, 20)
        s = "PART OF XINET GROUP"
        w = text_w(ld, s, f, spacing=5)
        text(ld, (W / 2 - w / 2, H - 150), s, f, DIM + (255,), spacing=5)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a4)))
        img.alpha_composite(layer)

    # Final scene: fade the whole video out to black.
    out = span(t, 0.92, 1.0)
    if out > 0:
        img = Image.blend(img, Image.new("RGBA", (W, H), BG + (255,)), ease_in_out(out))
    return img


# ───────────────────────────── timeline ─────────────────────────────
def build_timeline(shots):
    discover = Image.open(os.path.join(SHOTS, "ui-discover.png")).convert("RGB")
    library = Image.open(os.path.join(SHOTS, "ui-library.png")).convert("RGB")
    displays = Image.open(os.path.join(SHOTS, "ui-displays.png")).convert("RGB")
    perf = Image.open(os.path.join(SHOTS, "ui-performance.png")).convert("RGB")
    desktop = Image.open(os.path.join(SHOTS, "desktop-live.png")).convert("RGB")

    return [
        ("intro", 5.0, lambda t: scene_intro(t)),
        ("problem", 6.0, lambda t: scene_problem(t)),
        ("ui-discover", 5.5, lambda t: scene_ui(t, discover, "KATALOG",
                                                 "5.000+ wallpaper siap pakai",
                                                 "Cari, filter, dan unduh — semuanya di dalam aplikasi",
                                                 pan=(0.25, 0.15))),
        ("ui-library", 4.5, lambda t: scene_ui(t, library, "PUSTAKA",
                                               "Koleksi kamu, rapi",
                                               "Semua wallpaper lokal dan unduhan di satu tempat",
                                               pan=(-0.2, 0.1))),
        ("monitors", 5.5, lambda t: scene_monitors(t)),
        ("ui-displays", 4.5, lambda t: scene_ui(t, displays, "LAYAR",
                                                "Atur tiap monitor",
                                                "Pilih target, simpan profil, pulihkan dengan satu klik",
                                                pan=(0.15, -0.1))),
        ("pause", 6.0, lambda t: scene_pause(t)),
        ("ui-perf", 4.5, lambda t: scene_ui(t, perf, "PERFORMA",
                                            "Telemetri langsung",
                                            "CPU, RAM, dan FPS terlihat real-time",
                                            pan=(-0.15, 0.15))),
        ("features", 5.5, lambda t: scene_features(t)),
        ("outro", 5.0, lambda t: scene_outro(t)),
    ]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None

    os.makedirs(FRAME_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    shots = os.path.join(SHOTS)
    if not os.path.exists(os.path.join(shots, "ui-discover.png")):
        print("screenshots missing - run capture-ui-for-site.ps1 first")
        return 1

    timeline = build_timeline(shots)
    total_frames = int(sum(d for _, d, _ in timeline) * FPS)
    print("total frames: %d  (%.1f s at %d fps)" % (total_frames, total_frames / FPS, FPS))

    # Scenes are rendered as RGBA frames first, then blended with a short
    # crossfade so a transition is never an empty frame.
    CROSSFADE = int(0.5 * FPS)

    # Crossfading needs the outgoing scene's tail and the incoming scene's head.
    # Holding whole scenes in memory caused a MemoryError (a 6 s scene is 180
    # frames of 1920x1080 RGBA = ~1.5 GB), and holding every scene was ~13 GB.
    # Only the head of the next scene is needed for the blend, so that is all
    # that is kept: the rest of the scene is rendered afterwards, frame by frame.
    frame_no = 0

    def scene_frame(render, i, count):
        return render(i / max(1, count - 1))

    for idx, (name, duration, render) in enumerate(timeline):
        if only and only != name:
            continue

        count = int(duration * FPS)
        is_last = idx + 1 >= len(timeline)
        head = []
        if not is_last:
            next_duration, next_render = timeline[idx + 1][1], timeline[idx + 1][2]
            next_count = int(next_duration * FPS)
            head = [scene_frame(next_render, i, next_count) for i in range(min(CROSSFADE, next_count))]

        print("  scene %-14s %5.1fs  %4d frames" % (name, duration, count))

        for i in range(count):
            img = scene_frame(render, i, count)
            if head and i >= count - CROSSFADE:
                k = (i - (count - CROSSFADE)) / CROSSFADE
                j = min(len(head) - 1, int(k * CROSSFADE))
                img = Image.blend(img, head[j], ease_in_out(k))
            out = vignette(img.convert("RGB"), 0.42)
            out.save(os.path.join(FRAME_DIR, "f%05d.png" % frame_no), "PNG", compress_level=1)
            frame_no += 1
            # Release the frame immediately: at 1920x1080 a lingering reference
            # is 8 MB, and the loop runs 1560 times.
            img = None
            out = None
        head = None

    print("frames written to", FRAME_DIR)

    out = os.path.join(OUT_DIR, "lumawall-promo.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAME_DIR, "f%05d.png"),
        "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out,
    ]
    print("encoding:", " ".join(cmd[:8]), "...")
    subprocess.run(cmd, check=True)
    size = os.path.getsize(out) / 1024 / 1024
    print("wrote %s  (%.2f MB)" % (out, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
