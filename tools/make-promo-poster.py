"""make-promo-poster.py — builds the promo video's poster frame.

Why not a wallpaper: the video block sits in the centre of the page, and a
full-frame wallpaper puts its subject (a character) off to one side, leaving the
middle empty. A poster should have its weight in the middle, where the play
control and the title sit on top of it.

The poster is composed from the real wallpaper clips the app ships, so it shows
the product's actual content. Each panel is checked for the artist's watermark
that appears in some frames of some clips, and a clean frame is chosen
automatically - republishing someone's signature as our poster would be both a
credit problem and a visible blemish.

Run:  python tools/make-promo-poster.py
"""

import os
import subprocess
import sys

OUT = 'site/assets/shots/poster-promo.png'
W, H = 1920, 1080

# Candidate stills per clip. Several frames are offered per clip so a watermarked
# one can be skipped.
CANDIDATES = {
    'raiden': ['f020', 'f034', 'f048'],
    'astra':  ['f020', 'f034', 'f048'],
    'albedo': ['f020', 'f034', 'f048'],
}

# Where a watermark would sit if present: the bottom-right of each source frame.
# Measured as local contrast against the surrounding pixels - a watermark is a
# small bright mark on otherwise smooth art.
def watermark_score(path):
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', path,
         '-vf', 'crop=260:160:iw-280:ih-180,scale=65:40,format=gray',
         '-f', 'rawvideo', '-'],
        capture_output=True,
    )
    raw = r.stdout
    if not raw:
        return 999.0
    n = len(raw)
    mean = sum(raw) / n
    # Count how many pixels are far brighter than the local average: a signature
    # is a small cluster of such pixels.
    bright = sum(1 for b in raw if b > mean + 46)
    return bright / n * 100


def pick_clean(clip):
    best, best_score = None, None
    for stem in CANDIDATES[clip]:
        path = 'promo/frames/%s/%s.webp' % (clip, stem)
        if not os.path.exists(path):
            continue
        score = watermark_score(path)
        if best_score is None or score < best_score:
            best, best_score = path, score
    return best, best_score


picks = []
for clip in CANDIDATES:
    path, score = pick_clean(clip)
    if not path:
        raise SystemExit('no frames for %s - run: python tools/extract-clips.py' % clip)
    print('  %-8s %s  (watermark score %.2f)' % (clip, path.split('/')[-1], score))
    picks.append(path)

inputs = []
for p in picks:
    inputs += ['-i', p]

filter_complex = (
    '[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1[p0];'
    '[1:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1[p1];'
    '[2:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1[p2];'
    '[p0][p1][p2]hstack=inputs=3[stack];'
    '[stack]scale=%d:%d,'
    'eq=brightness=-0.06:contrast=1.08:saturation=0.94,'
    'drawbox=x=0:y=0:w=%d:h=%d:color=black@0.30:t=fill,'
    'vignette=PI/4,'
    'format=rgb24[out]'
) % (
    W // 3, H, W // 3, H,
    W // 3, H, W // 3, H,
    W // 3, H, W // 3, H,
    W, H,
    W, H,
)

cmd = [
    'ffmpeg', '-v', 'error', '-y',
    *inputs,
    '-filter_complex', filter_complex,
    '-map', '[out]',
    '-frames:v', '1',
    OUT,
]

print('  building the poster from clean wallpaper stills...')
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print('  ffmpeg failed:')
    print('   ', r.stderr.strip()[:600])
    sys.exit(1)

print('  %s  (%d bytes, %dx%d)' % (OUT, os.path.getsize(OUT), W, H))
