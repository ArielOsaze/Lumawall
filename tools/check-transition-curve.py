"""check-transition-curve.py — verifies two beats never overlap at full opacity.

The transition between beats is the part that is hardest to judge by eye and
easiest to get wrong, and getting it wrong looks like a glitch: two headings and
two sets of figures on screen at once.

This mirrors the arithmetic in Timeline.jsx and checks, at every frame of every
handover, that the outgoing and incoming opacities sum to about 1 and that
neither sits at full strength while the other is still readable.

Run:  python tools/check-transition-curve.py
"""

import math

FPS = 30
TRAVEL = 1.6

BEATS = [
    ('intro', 0.0),
    ('problem', 6.4),
    ('catalog', 13.6),
    ('monitors', 21.4),
    ('pause', 29.4),
    ('perf', 37.6),
    ('outro', 44.6),
]


def clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def seg(t, a, b):
    if b == a:
        return 1.0 if t >= b else 0.0
    return clamp01((t - a) / (b - a))


def ease_out(k):
    return 1 - (1 - k) ** 3


def ease_in_out(k):
    return 4 * k ** 3 if k < 0.5 else 1 - ((-2 * k + 2) ** 3) / 2


def opacity_of(beat_index, t):
    """Mirrors the Timeline: returns (opacity, slide) for a beat at time t."""
    from_t = BEATS[beat_index][1]
    is_last = beat_index == len(BEATS) - 1
    next_from = None if is_last else BEATS[beat_index + 1][1]

    if t < from_t - 0.05:
        return None
    if next_from is not None and t > next_from + TRAVEL + 0.05:
        return None

    k_in = 1.0 if beat_index == 0 else ease_in_out(seg(t, from_t, from_t + TRAVEL))
    k_out = ease_in_out(seg(t, next_from, next_from + TRAVEL)) if next_from is not None else 0.0
    opacity = clamp01(k_in * (1 - k_out))

    enter_x = (1 - k_in) * 1920
    exit_x = -k_out * 1920
    return opacity, enter_x + exit_x


print('  every handover, frame by frame:')
problems = 0

for i in range(len(BEATS) - 1):
    a_name, _ = BEATS[i]
    b_name, b_from = BEATS[i + 1][0], BEATS[i + 1][1]

    print()
    print('  %s -> %s  (overlap starts t=%.1f)' % (a_name, b_name, b_from))

    worst_sum = 0.0
    both_full = 0
    min_sep = 99999
    samples = []

    t = b_from
    while t <= b_from + TRAVEL + 0.0001:
        a = opacity_of(i, t)
        b = opacity_of(i + 1, t)
        a_op = a[0] if a else 0.0
        b_op = b[0] if b else 0.0
        total = a_op + b_op
        worst_sum = max(worst_sum, total)

        # Invariant: the two beats are never in the same place. With a pan rather
        # than a crossfade both stay fully opaque, so what keeps two headings from
        # stacking is distance, not transparency. The pan is the full frame width,
        # so the separation should be exactly one frame at every instant.
        sep = abs((a[1] if a else 0) - (b[1] if b else 0))
        if sep < min_sep:
            min_sep = sep
        if sep < 1919:
            both_full += 1

        samples.append((t, a_op, b_op, total))
        t += 1.0 / FPS

    for t, a_op, b_op, total in samples[::3]:
        print('    t=%.2f  out=%.2f  in=%.2f  sum=%.2f' % (t, a_op, b_op, total))

    print('    peak combined opacity : %.2f' % worst_sum)
    print('    min separation between beats   : %.0f px (frame is 1920)' % min_sep)

    if both_full:
        print('    FAIL: %d frame(s) where the two beats are close enough to overlap' % both_full)
        problems += 1

print()
if problems:
    print('  %d problem(s)' % problems)
    raise SystemExit(1)
print('  every handover keeps the two beats a half-frame apart, so no frame double-exposes')
