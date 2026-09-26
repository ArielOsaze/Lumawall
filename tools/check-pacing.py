"""check-pacing.py — the promo is cut like a commercial, not held like a deck.

Why this exists, and why it is the check that was missing:

Six rounds of work went into this promo's transitions, and the note that came back
every time was "still a slide". Every round improved the joins. None of them measured
the thing the viewer was actually describing:

  · how long each shot is held, and
  · whether anything moves during that time.

A storyboard of every second of the finished piece showed seven shots of 6-8 seconds,
each of which finished animating after 1-3 seconds and then held a still frame for the
rest. That is a slide. The joins between them were, by then, excellent.

So this checks the two properties that make something a slideshow:

  1. HOLD TIME. No shot may run longer than MAX_SHOT. A deck holds a message for
     6-10 seconds; a motion piece cuts every 2-5.
  2. DEAD AIR. Sampled across the whole piece, the frame must change between
     consecutive samples everywhere. A run of near-identical samples inside one shot
     is a held still, and that is the failure this exists to catch.

Both are measured on the rendered video, because both are properties of the output -
a scene can be written to move and still produce a still frame if its animation has
already finished.

Run:  python tools/check-pacing.py [video]
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
from shotlist import windows, total, shots

# The longest a shot may be held. A broadcast commercial cuts every 1-3 seconds; this
# piece is a product explainer, so it can breathe more than that - but not to the
# 6-8 seconds of a slide deck, which is what the seven-shot version did.
MAX_SHOT = 5.0

# How much the frame must change between two samples half a second apart for the
# shot to count as moving. Measured on this material: a held frame reads under 0.8,
# a scene with its own drift reads over 1.5.
MIN_MOTION = 0.9

# How long a run of near-still samples may be before it counts as dead air.
MAX_STILL_RUN = 3      # 3 x 0.5s = 1.5 seconds


# A cut shows as a large frame-to-frame change at the boundary. Measured on this
# material: a real cut reads 11-33, a whip smear at a cut reads 5-9, and ordinary
# motion inside a shot reads under 4.
CUT_THRESHOLD = 8.0


def cut_jump(video, cut):
    """How much the frame changes across a cut, measured either side of it."""
    import numpy as np
    from PIL import Image

    os.makedirs('build/pacing', exist_ok=True)
    frames = []
    for t in (cut - 0.08, cut + 0.02, cut + 0.12):
        fp = 'build/pacing/j.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(max(0, t)), '-i', video,
                        '-frames:v', '1', '-vf', 'scale=240:135', '-y', fp],
                       capture_output=True)
        if not os.path.exists(fp):
            return None
        frames.append(np.asarray(Image.open(fp).convert('L')).astype(float))
    if len(frames) < 3:
        return None
    return float(max(np.abs(frames[1] - frames[0]).mean(),
                     np.abs(frames[2] - frames[1]).mean()))


def count_cuts(video, duration, threshold=12.0):
    """How many hard cuts the video contains.

    A cut is a frame where the image changes far more than the shots on either side
    of it do. Counting them is what distinguishes a seven-shot render from a
    thirteen-shot one - which is the only way to tell that the file on disk is not
    the file the source describes.
    """
    import numpy as np
    from PIL import Image

    os.makedirs('build/pacing', exist_ok=True)
    step = 1 / 15.0                     # sample at 15 fps: fine enough to catch a cut
    n = int(duration / step)
    prev = None
    diffs = []
    for i in range(n):
        t = i * step
        fp = 'build/pacing/c.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
                        '-frames:v', '1', '-vf', 'scale=160:90', '-y', fp],
                       capture_output=True)
        if not os.path.exists(fp):
            continue
        cur = np.asarray(Image.open(fp).convert('L')).astype(float)
        if prev is not None:
            diffs.append(float(np.abs(cur - prev).mean()))
        prev = cur

    if len(diffs) < 10:
        return None

    d = np.asarray(diffs)
    # A cut is a spike well above the local level. The whip smear spreads it over two
    # or three samples, so the count is of clusters, not of individual spikes.
    spikes = d > max(threshold, np.percentile(d, 97))
    clusters = 0
    for i, s in enumerate(spikes):
        if s and (i == 0 or not spikes[i - 1]):
            clusters += 1
    return clusters


def main():
    video = sys.argv[1] if len(sys.argv) > 1 else promo_video()
    if not video or not os.path.exists(video):
        print('  no promo video found')
        return 1

    all_cuts = shots()
    shot_windows = windows()
    if not all_cuts:
        print('  could not read the shot list from Direction.jsx')
        return 1

    problems = []

    # ── 0. does the video match the current cut list? ────────────────────────
    #
    # The cut list is read from Direction.jsx, which is the source - but the video on
    # disk may be an older render made from a different list. Checking the list
    # against itself would pass an out-of-date render forever, which is the exact
    # failure this file exists to prevent. So the two are compared first.
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', video], capture_output=True, text=True)
    try:
        video_dur = float(probe.stdout.strip())
    except ValueError:
        print('  cannot read the video duration')
        return 1

    expected = total()
    if abs(video_dur - expected) > 0.5:
        problems.append('the video is %.1fs but the cut list describes %.1fs - the '
                        'render is out of date' % (video_dur, expected))

    # ── 0b. is there a cut at each time the list says? ───────────────────────
    #
    # Counting cuts in the video and comparing the total was the first attempt, and it
    # was unreliable: the whip smear spreads a cut over two or three samples, so the
    # count came back low (10 against 12) and a current render was reported as stale.
    #
    # The property that actually matters is not the total, it is that a cut happens
    # WHERE THE LIST SAYS. Checking each boundary directly is both more precise and
    # more useful: it names the boundary that is missing.
    missing = []
    for name, cut in all_cuts[1:]:
        jump = cut_jump(video, cut)
        if jump is None:
            continue
        if jump < CUT_THRESHOLD:
            missing.append((name, cut, jump))

    if missing:
        problems.append('%d of %d cuts are missing from the video - the render is out '
                        'of date (first: %s at %.1fs, change %.1f)'
                        % (len(missing), len(all_cuts) - 1, missing[0][0], missing[0][1], missing[0][2]))
        print()
        print('  cuts not found:')
        for name, cut, jump in missing[:6]:
            print('    %-12s at %5.1fs   change %.1f (needs %.1f)'
                  % (name, cut, jump, CUT_THRESHOLD))

    # ── 1. hold time ─────────────────────────────────────────────────────────
    print()
    print('  hold time per shot (max %.1fs):' % MAX_SHOT)
    print()
    for name, a, b in shot_windows:
        length = b - a
        flag = ''
        if length > MAX_SHOT:
            flag = '  TOO LONG'
            problems.append('%s is held for %.1fs - a deck holds a message this long'
                            % (name, length))
        bar = '#' * int(round(length * 4))
        print('    %-12s %5.1fs  %s%s' % (name, length, bar, flag))

    lengths = [b - a for _, a, b in shot_windows]
    print()
    print('    %d shots, %.1f-%.1fs, average %.1fs' % (
        len(shot_windows), min(lengths), max(lengths), sum(lengths) / len(lengths)))

    # ── 2. dead air, measured on the render ──────────────────────────────────
    print()
    print('  motion across the piece (sampled every 0.5s):')
    print()

    os.makedirs('build/pacing', exist_ok=True)
    step = 0.5
    n = int(total() / step)

    prev = None
    series = []
    for i in range(1, n):
        t = i * step
        fp = 'build/pacing/f.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
                        '-frames:v', '1', '-vf', 'scale=320:180', '-y', fp],
                       capture_output=True)
        if not os.path.exists(fp):
            continue
        cur = np.asarray(Image.open(fp).convert('L')).astype(float)
        if prev is not None:
            series.append((t, float(np.abs(cur - prev).mean())))
        prev = cur

    if not series:
        print('    could not read frames from the video')
        return 1

    line = ''.join('#' if d > 4 else ('+' if d > 2 else ('.' if d >= MIN_MOTION else ' '))
                   for _, d in series)
    print('    0s' + ' ' * max(1, len(line) // 2 - 4) + '%.0fs' % total())
    print('    ' + line)
    print('    (# big change   + some   . moving   space still)')

    # The longest run of still samples.
    run = 0
    worst = 0
    worst_at = None
    for t, d in series:
        if d < MIN_MOTION:
            run += 1
            if run > worst:
                worst = run
                worst_at = t
        else:
            run = 0

    stills = sum(1 for _, d in series if d < MIN_MOTION)
    print()
    print('    still samples: %d of %d (%.0f%%)' % (stills, len(series), 100 * stills / len(series)))
    print('    longest still run: %.1fs%s' % (
        worst * step, ' ending at %.1fs' % worst_at if worst_at else ''))

    if worst > MAX_STILL_RUN:
        problems.append('the frame holds still for %.1fs - that is dead air, and it is '
                        'what reads as a slide' % (worst * step))

    print()
    if problems:
        print('  PROBLEMS:')
        for p in problems:
            print('    ' + p)
        print()
        print('  A shot that has finished moving and is waiting to be cut is a slide,')
        print('  however good the cut into it is. Either shorten the shot or give it')
        print('  something that keeps moving for its whole length.')
        return 1

    print('  no shot is held longer than %.1fs and the frame never stops moving' % MAX_SHOT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
