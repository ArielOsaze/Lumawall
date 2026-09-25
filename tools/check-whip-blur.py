"""check-whip-blur.py — verifies the motion blur matches the motion.

This is the arithmetic that three earlier transitions got wrong. A pan with blur
still read as a slide because the blur was 26px while the content moved 1920px:
1/80th of the motion, so the frame showed two distinct half-scenes with soft edges
rather than one smear.

The relationship that matters:

    pixels moved per captured frame = distance / (handover_seconds * fps)

At 30fps, a handover has ~10 frames. If the content moves 1080px in that time, it
moves ~108px per frame on average and about twice that at the peak of an easeInOut
curve. A blur below roughly half the per-frame distance reads as a soft edge
instead of as motion.

Run:  python tools/check-whip-blur.py
"""

import math
import sys

FPS = 30
HANDOVER = 0.26
TRAVEL_X = 1080
TRAVEL_Y = 620

# Mirrors WHIP_BLUR in MotionFilters.jsx. This is the standard deviation of a
# Gaussian along the axis of travel only; the perpendicular axis is sharp.
WHIP_BLUR = 150
WHIP_BLUR_Y = WHIP_BLUR * 0.35

# A Gaussian's visible smear is roughly four standard deviations wide, which is
# what has to cover the gap between two captured frames.
SIGMA_TO_WIDTH = 4.0


print('  handover: %.2fs at %d fps  ->  %.1f frames' % (HANDOVER, FPS, HANDOVER * FPS))
print()

problems = []

for label, distance, blur in [('horizontal whip', TRAVEL_X, WHIP_BLUR),
                              ('vertical whip', TRAVEL_Y, WHIP_BLUR_Y)]:
    avg_per_frame = distance / (HANDOVER * FPS)
    peak_per_frame = avg_per_frame * 2.0  # easeInOut peaks at about twice average
    smear_width = blur * SIGMA_TO_WIDTH
    ratio = smear_width / peak_per_frame

    print('  %s' % label)
    print('    distance              : %d px' % distance)
    print('    per frame (average)   : %.1f px' % avg_per_frame)
    print('    per frame (peak)      : %.1f px' % peak_per_frame)
    print('    blur (std dev)        : %.1f px' % blur)
    print('    visible smear width   : %.1f px' % smear_width)
    print('    smear / peak distance : %.2f' % ratio)

    # Below 0.8 the blur does not cover the gap between frames, and the eye sees
    # two positions rather than one movement.
    if ratio < 0.6:
        problems.append('%s: the smear covers only %.0f%% of the per-frame movement' % (label, ratio * 100))
        print('    VERDICT               : TOO LITTLE - reads as a soft-edged slide')
    elif ratio > 2.2:
        problems.append('%s: the smear is %.1fx the movement, so the content dissolves' % (label, ratio))
        print('    VERDICT               : TOO MUCH - content dissolves into fog')
    else:
        print('    VERDICT               : OK - a directional smear covering the motion')
    print()

# The handover has to be fast enough that the eye cannot track it frame by frame.
# Above about 0.5s the movement becomes legible as a slide rather than a whip.
if HANDOVER > 0.5:
    problems.append('the handover is %.2fs; above ~0.5s the eye can track the slide' % HANDOVER)
    print('  handover duration: TOO SLOW (%.2fs)' % HANDOVER)
else:
    print('  handover duration: OK (%.2fs - faster than the eye tracks)' % HANDOVER)

print()
if problems:
    print('  %d problem(s):' % len(problems))
    for p in problems:
        print('    ' + p)
    sys.exit(1)
print('  the blur matches the motion, and the handover is fast enough to read as a whip')
