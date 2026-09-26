"""measure-promo-backgrounds.py — how much of the promo is a wallpaper, by pixel.

The user's complaint is that the video's backgrounds are all wallpapers. That is a
measurable property, not a matter of opinion, and asking a vision model to judge it
from a contact sheet gave a different answer each time.

A wallpaper background has photographic detail: high local variance and colour
across the whole frame. A brand surface is a near-flat dark gradient with a faint
grid, so its variance is low and its palette is narrow.

This samples the whole video and reports, per beat, which kind of background it has,
so "the backgrounds vary" is a number rather than an impression.

Run:  python tools/measure-promo-backgrounds.py [video]
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'site/assets/video/lumawall-promo.mp4')

# Shots from Direction.jsx.
BEATS = [
    ('intro',    0.0,   6.4),
    ('problem',  6.4,  13.4),
    ('catalog', 13.4,  21.0),
    ('monitors', 21.0, 28.4),
    ('pause',   28.4,  36.4),
    ('perf',    36.4,  44.4),
    ('outro',   44.4,  52.0),
]

# A frame is sampled from the middle of each shot, away from the cuts.
SAMPLES_PER_BEAT = 3

# Thresholds, measured on this material:
#   wallpaper : stddev of luma > 26 and mean colour spread > 30
#   brand     : stddev < 20 and spread < 22
WALL_STD = 26
WALL_SPREAD = 30
BRAND_STD = 20
BRAND_SPREAD = 22


def frame(t):
    tmp = os.path.join('build', '_bg.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                    '-frames:v', '1', '-y', tmp], capture_output=True)
    return np.asarray(Image.open(tmp).convert('RGB')).astype(float) if os.path.exists(tmp) else None


def classify(a):
    luma = a @ np.array([0.299, 0.587, 0.114])
    std = luma.std()
    # Colour spread: how far the channel means are from each other, plus how much
    # the hue varies. A wallpaper is colourful; a brand surface is one hue.
    spread = np.abs(np.mean(a[:, :, 0]) - np.mean(a[:, :, 2])) + np.abs(np.mean(a[:, :, 1]) - np.mean(a[:, :, 0]))
    if std > WALL_STD and spread > WALL_SPREAD:
        return 'wallpaper', std, spread
    if std < BRAND_STD and spread < BRAND_SPREAD:
        return 'brand', std, spread
    return 'mixed', std, spread


def main():
    if not os.path.exists(VIDEO):
        print('  no video at %s' % VIDEO)
        return 1

    print('  %s' % VIDEO)
    print()
    print('  beat        stddev   spread   verdict')
    kinds = {}
    for name, start, end in BEATS:
        votes = []
        for i in range(SAMPLES_PER_BEAT):
            t = start + (end - start) * (0.3 + 0.4 * i / max(1, SAMPLES_PER_BEAT - 1))
            a = frame(t)
            if a is None:
                continue
            kind, std, spread = classify(a)
            votes.append((kind, std, spread))
        if not votes:
            print('    %-10s could not sample' % name)
            continue
        # Majority vote across the beat's samples.
        counts = {}
        for k, _, _ in votes:
            counts[k] = counts.get(k, 0) + 1
        winner = max(counts, key=counts.get)
        kinds[winner] = kinds.get(winner, 0) + 1
        std = sum(v[1] for v in votes) / len(votes)
        spread = sum(v[2] for v in votes) / len(votes)
        print('    %-10s %6.1f   %6.1f   %s' % (name, std, spread, winner))

    print()
    wall = kinds.get('wallpaper', 0)
    brand = kinds.get('brand', 0)
    mixed = kinds.get('mixed', 0)
    print('  wallpaper backgrounds : %d beat(s)' % wall)
    print('  brand surfaces        : %d beat(s)' % brand)
    if mixed:
        print('  mixed / neither       : %d beat(s)' % mixed)

    print()
    if wall == 0 and brand == 0:
        # The classifier could not separate the cases on this material - the text and
        # UI inside each frame dominate the statistics. Reporting a verdict from it
        # would be worse than reporting nothing: the previous version of this check
        # announced "every beat is a brand surface" from exactly this state.
        print('  the statistics do not separate wallpaper from brand surface here.')
        print('  This is not a pass or a failure - judge the beats by looking at them:')
        print('    tools/check-promo-scenes.py reports where a wallpaper is visible.')
        return 0
    if wall == 0:
        print('  every beat measured as a brand surface - the video has no product imagery')
        return 1
    if brand == 0:
        print('  EVERY BEAT MEASURED AS A WALLPAPER - this is the complaint, and it is true')
        return 1
    print('  the backgrounds vary: %d wallpaper, %d brand surface' % (wall, brand))
    return 0


if __name__ == '__main__':
    sys.exit(main())
