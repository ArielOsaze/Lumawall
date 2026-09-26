"""make-hero-loop.py — builds the animated hero background from a wallpaper.

The user asked for a hero that is attractive, has red in it to match the brand,
and moves, so the page demonstrates the product instead of describing it.

Why not just point a <video> at the wallpaper file:

  · it is 12.7 MB at 1920x1080, which is the whole page's budget for a background
  · the wallpaper is portrait-ish composition, so covering a wide, short hero band
    crops it unpredictably
  · a wallpaper loop does not necessarily join seamlessly, and a visible jump
    every 21 seconds on the front page is worse than no motion
  · the type sits on the left, and a wallpaper has no dark side for it

So this composes a hero-sized loop from the source: cropped for the hero's aspect
with the subject kept right, a smooth left-to-right darkening baked in, and the
end cross-faded into the start so the loop has no seam. It is encoded small and
with no audio, because it is a background.

Run:  python tools/make-hero-loop.py
"""

import os
import subprocess
import sys

SRC = os.path.join(
    os.path.expandvars(r'%LOCALAPPDATA%'),
    'LumaWall', 'Wallpapers', 'Albedo’s Dark Grace (Overlord).mp4',
)
OUT = 'site/assets/video/hero-loop.mp4'
POSTER = 'site/assets/shots/hero-bg.jpg'

if not os.path.exists(SRC):
    sys.exit('missing %s' % SRC)

# The hero band is wide and short, so the source is cropped to 16:9 and anchored so
# the figure stays right of centre where the text is not.
#
# This was 1280x720, and that was wrong: the hero renders at the viewport width, so
# on a 1920-wide screen a 1280px clip is upscaled 1.5x and reads as soft. The user
# described it as "videonya pecah", and they were right. The source is 1920x1080, so
# there is no reason to throw that away - the file is larger, but it is the first
# thing on the page and the one place where softness is obvious.
W, H = 1920, 1080

# How much of the loop to cross-fade into itself, in seconds. Without this the
# loop point is a hard cut: the wallpaper does not end where it began.
XFADE = 1.0

# The source's length, read rather than assumed, so the cross-fade offset is
# correct if the wallpaper file is ever replaced.
def duration_of(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit('cannot read the duration of %s' % path)


SRC_DURATION = duration_of(SRC)
# The main part runs from XFADE to the end, so the cross-fade starts that far
# before the end of the main part.
XFADE_OFFSET = SRC_DURATION - XFADE * 2

# The left-hand darkening, as a smooth alpha ramp. A drawbox left a visible
# vertical seam on the earlier hero image, so this uses a per-pixel ramp.
DARKEN = (
    "format=rgba,"
    "geq="
    "r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
    f"a='255*(0.34+0.66*pow(min(1,max(0,X/{int(W * 0.58)})),1.6))'"
)

# Where the subject sits after the crop. 0.62 keeps her in the right third.
CROP_ANCHOR = 0.62

filters = (
    # 1. crop to the hero's aspect, subject kept right
    f'scale={W}:{H}:force_original_aspect_ratio=increase,'
    f'crop={W}:{H}:(iw-{W})*{CROP_ANCHOR}:0,'
    # 2. a slight grade so the artwork and the accent sit together
    'eq=brightness=-0.05:contrast=1.08:saturation=0.98,'
    # 3. the left-hand ramp for the type
    f'{DARKEN},'
    'format=yuv420p'
)

# ── the seamless loop ────────────────────────────────────────────────────────
#
# Split the clip, hold the first XFADE seconds back, and cross-fade the tail into
# it. The result is a clip whose last frame is the first frame, so a loop has no
# visible join.
cmd = [
    'ffmpeg', '-v', 'error', '-y',
    '-i', SRC,
    '-filter_complex',
    f'[0:v]{filters},split[a][b];'
    f'[a]trim=start={XFADE},setpts=PTS-STARTPTS[main];'
    f'[b]trim=start=0:end={XFADE},setpts=PTS-STARTPTS[head];'
    f'[main][head]xfade=transition=fade:duration={XFADE}:'
    f'offset={XFADE_OFFSET:.3f}[v]',
    '-map', '[v]',
    # A background does not need the highest bitrate, but it must not be visibly
    # soft. crf 27 at 1280x720 was 1.4 Mbps and the upscale to a 1920-wide hero made
    # it look broken. At full resolution, crf 22 keeps the artwork clean while the
    # file stays a few megabytes.
    '-c:v', 'libx264',
    '-preset', 'slow',
    '-crf', '22',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    '-an',
    '-t', f'{SRC_DURATION - XFADE:.2f}',
    OUT,
]

print('  source: %.1fs  ->  loop: %.1fs with a %.1fs cross-fade' % (
    SRC_DURATION, SRC_DURATION - XFADE, XFADE))
print('  composing the hero loop...')
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print('  ffmpeg failed:')
    print('   ', r.stderr.strip()[:700])
    sys.exit(1)

size_mb = os.path.getsize(OUT) / 1048576
print('  %s  (%.2f MB, %dx%d)' % (OUT, size_mb, W, H))

# ── the poster ───────────────────────────────────────────────────────────────
#
# A still from the loop, graded the same way, so the hero has an image before the
# video loads and nothing shifts when it starts. Taken a little way in, so it is
# not the frame the video begins on.
print('  extracting the poster...')
r = subprocess.run(
    ['ffmpeg', '-v', 'error', '-y', '-ss', '2', '-i', OUT,
     '-frames:v', '1', '-q:v', '4', POSTER],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print('  poster failed:', r.stderr.strip()[:300])
    sys.exit(1)
print('  %s  (%d bytes)' % (POSTER, os.path.getsize(POSTER)))
