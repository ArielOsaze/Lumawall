"""extract-clips.py — turns the wallpaper videos into image sequences for the promo.

Why image sequences instead of <video> elements:

  A <video> plays from the wall clock. During a frame-by-frame render the browser
  advances it independently of the renderer, so frame N would show a different
  picture on every run — and the same frame could be captured twice or skipped.
  The output would not be reproducible and the wallpaper would visibly stutter.

  Picking `frames[floor(t * fps) % count]` makes the wallpaper's position an exact
  function of the render time, so it plays smoothly and every render is identical.

Why 0-based numbering:

  ffmpeg numbers output frames from 1 by default, so the sequence is f001..f060.
  The component computes an index from the clock, which is naturally 0-based, and
  asked for f000 — which does not exist. Every image failed to load and the
  wallpaper sat on its first frame for the whole video: the promo for a moving
  wallpaper contained a still one.

  `-start_number 0` makes the files match the index the code computes.

Run:
  python tools/extract-clips.py
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(os.environ['LOCALAPPDATA'], 'LumaWall', 'Wallpapers')
OUT = os.path.join(ROOT, 'promo', 'frames')

# 12 fps is enough: these are mostly darkened background textures and the motion
# still reads. A higher rate would multiply the frame count for no visible gain.
FPS = 12
SECONDS = 5

CLIPS = [
    ('moonlit-reverie-raiden-shogun-genshin-impact_24fps.mp4', 'raiden'),
    ('Astra Yao - Zenless Zone Zero.mp4', 'astra'),
    ("Albedo's Dark Grace (Overlord).mp4", 'albedo'),
    ('I-14 Thousand-Faced Nothingness.mp4', 'i14'),
]


def main():
    if not os.path.isdir(LIB):
        print('wallpaper library not found at %s' % LIB)
        return 1

    os.makedirs(OUT, exist_ok=True)
    manifest = {}

    for name, slug in CLIPS:
        src = os.path.join(LIB, name)
        if not os.path.exists(src):
            # The library is the user's own collection, so a missing file is
            # expected on another machine. Try a loose match before giving up.
            cands = [f for f in os.listdir(LIB)
                     if f.lower().startswith(slug.lower()) or slug in f.lower()]
            if not cands:
                print('  skip %-10s (no source: %s)' % (slug, name))
                continue
            src = os.path.join(LIB, cands[0])
            print('  %-10s using %s' % (slug, cands[0]))

        dest = os.path.join(OUT, slug)
        os.makedirs(dest, exist_ok=True)
        for f in os.listdir(dest):
            os.remove(os.path.join(dest, f))

        subprocess.run([
            'ffmpeg', '-v', 'error', '-y',
            '-i', src,
            '-t', str(SECONDS),
            '-an',
            '-vf', 'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=%d' % FPS,
            '-c:v', 'libwebp', '-quality', '78', '-compression_level', '6',
            # 0-based, so the filenames match the index the component computes.
            '-start_number', '0',
            os.path.join(dest, 'f%03d.webp'),
        ], check=True)

        files = sorted(os.listdir(dest))
        size = sum(os.path.getsize(os.path.join(dest, f)) for f in files)
        manifest[slug] = len(files)
        print('  %-10s %3d frames  %5.1f MB  %s' % (slug, len(files), size / 1048576, files[0]))

    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    total = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fs in os.walk(OUT) for f in fs
    )
    print()
    print('  total: %.1f MB in %s' % (total / 1048576, OUT))
    print('  (render-only; never deployed)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
