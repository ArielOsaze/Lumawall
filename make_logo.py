"""
Generates the LumaWall brand mark used by the app, the shortcut and the
installer: a dark squircle with a crimson "L" wave and a cyan accent bar.

Outputs:
  app-logo.png  512x512  (in-app title bar / installer art)
  app.ico       16..256  (exe icon, shortcut, uninstall entry)
"""
import io
import math
import os
import struct
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\LumaWall"

# Brand palette (must match MainWindow.cs so shell and icon agree)
INK_TOP = (16, 19, 26)
INK_BOTTOM = (7, 8, 11)
CRIMSON = (255, 46, 67)
CRIMSON_HI = (255, 96, 116)
CYAN = (34, 211, 238)
WHITE = (242, 245, 250)

SS = 4  # supersampling factor


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


def build_master(size=512):
    S = size * SS
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # --- plate: dark gradient with a warm crimson bloom top-left -----------
    plate = vertical_gradient(size, INK_TOP, INK_BOTTOM).convert("RGBA")
    bloom = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    bd.ellipse([-S * 0.35, -S * 0.45, S * 0.95, S * 0.65], fill=CRIMSON + (54,))
    bd.ellipse([S * 0.45, S * 0.35, S * 1.35, S * 1.25], fill=CYAN + (34,))
    bloom = bloom.filter(ImageFilter.GaussianBlur(S * 0.09))
    plate = Image.alpha_composite(plate, bloom)

    # --- mark: "L" wave built from three swept bars ------------------------
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)

    # Three ascending panels read as an "L" run and as stacked wallpaper panes.
    panels = [
        # (x0, y0, x1, y1, color)
        (0.26, 0.62, 0.38, 0.76, CRIMSON),
        (0.26, 0.44, 0.38, 0.60, CRIMSON_HI),
        (0.26, 0.26, 0.38, 0.42, CRIMSON),
        (0.40, 0.62, 0.74, 0.76, WHITE),
        (0.40, 0.44, 0.60, 0.60, WHITE),
        (0.40, 0.26, 0.52, 0.42, WHITE),
        (0.76, 0.62, 0.86, 0.76, CYAN),
        (0.76, 0.44, 0.86, 0.60, CYAN),
        (0.76, 0.26, 0.86, 0.42, CYAN),
    ]
    radius = int(S * 0.022)
    for (x0, y0, x1, y1, color) in panels:
        md.rounded_rectangle(
            [int(x0 * S), int(y0 * S), int(x1 * S), int(y1 * S)],
            radius=radius,
            fill=color + (255,),
        )

    # Sweep highlight so the mark reads as glass, not flat stickers.
    sheen = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.polygon(
        [(0.22 * S, 0.22 * S), (0.92 * S, 0.34 * S), (0.92 * S, 0.44 * S), (0.22 * S, 0.34 * S)],
        fill=(255, 255, 255, 26),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(S * 0.012))
    mark = Image.alpha_composite(mark, sheen)

    base = Image.alpha_composite(base, plate)
    base = Image.alpha_composite(base, mark)

    # --- inner rim: crisp 1px light edge for the glass panel look ----------
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    r = int(size * SS * 0.235)
    rd.rounded_rectangle([1, 1, S - 2, S - 2], radius=r - 1, outline=(255, 255, 255, 34), width=max(1, int(SS * 0.9)))
    base = Image.alpha_composite(base, rim)

    base = base.resize((size, size), Image.LANCZOS)
    base.putalpha(squircle_mask(size))
    return base


def main():
    master = build_master(512)
    png_path = os.path.join(OUT_DIR, "app-logo.png")
    master.save(png_path, "PNG")
    print("wrote", png_path)

    # Pillow's ICO writer keeps only one frame when append_images is used with
    # sizes, so the multi-resolution container is assembled by hand: Windows
    # picks 256px for the taskbar and 16px for the list view, and a single-entry
    # ICO makes the shell fall back to a generic icon.
    ico_path = os.path.join(OUT_DIR, "app.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    pngs = []
    for s in sizes:
        frame = master.resize((s, s), Image.LANCZOS)
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        pngs.append((s, buf.getvalue()))

    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = b""
    body = b""
    for (s, data) in pngs:
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    with open(ico_path, "wb") as fh:
        fh.write(header + entries + body)
    print("wrote", ico_path, "sizes", sizes)


if __name__ == "__main__":
    main()
