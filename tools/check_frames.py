"""check_frames.py — verifies a rendered video has no empty frames.

Why this exists: a missing import made one scene throw, React unmounted the whole
tree, and 46 seconds of the promo rendered as pure black. The renderer reported
success, the duration was correct, and the file size looked plausible. Only a
pixel scan caught it.

The check measures two independent things, because either alone gives false
results:

  mean brightness  - catches a fully black frame
  edge energy      - catches a frame that is dark but textured (a real dark scene)
                     versus one that is genuinely empty

A frame is only reported as empty when BOTH are at the floor. A moody dark scene
has low brightness but real structure; a failed render has neither.

Usage:
  python tools/check_frames.py build/preview.mp4
  python tools/check_frames.py site/assets/video/lumawall-promo.mp4 --expect 52
"""

import argparse
import os
import subprocess
import sys

W, H = 320, 180


def load_gray(path, fps):
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', path, '-vf',
         'fps=%s,scale=%d:%d,format=gray' % (fps, W, H),
         '-f', 'rawvideo', '-'],
        capture_output=True)
    if r.returncode != 0:
        raise SystemExit('ffmpeg failed:\n' + r.stderr.decode(errors='replace')[-800:])
    return r.stdout


def score(buf):
    mean = sum(buf) / len(buf)
    edges = 0
    n = 0
    for y in range(0, H, 4):
        base = y * W
        for x in range(0, W - 1, 4):
            edges += abs(buf[base + x] - buf[base + x + 1])
            n += 1
    return mean, edges / max(1, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video', nargs='?', default=None)
    ap.add_argument('--fps', type=float, default=4, help='sampling rate for the scan')
    ap.add_argument('--expect', type=float, default=None, help='expected duration in seconds')
    ap.add_argument('--brightness', type=float, default=12.0)
    ap.add_argument('--edges', type=float, default=1.2)
    args = ap.parse_args()
    if not args.video:
        # The promo's filename carries a content hash now, so the path is resolved
        # rather than passed in.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from promo_path import promo_video
        args.video = promo_video()
        if not args.video:
            raise SystemExit('no promo video found in site/assets/video')

    raw = load_gray(args.video, args.fps)
    size = W * H
    count = len(raw) // size
    if count == 0:
        raise SystemExit('no frames read from ' + args.video)

    # Duration, read from the container rather than inferred from the sample count.
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', args.video], capture_output=True, text=True)
    try:
        duration = float(p.stdout.strip())
    except ValueError:
        duration = count / args.fps

    empties = []
    worst = None
    for i in range(count):
        buf = raw[i * size:(i + 1) * size]
        mean, edges = score(buf)
        t = i / args.fps
        if mean < args.brightness and edges < args.edges:
            empties.append((round(t, 2), round(mean, 1), round(edges, 1)))
        if worst is None or edges < worst[2]:
            worst = (round(t, 2), round(mean, 1), round(edges, 1))

    print('  file      : %s' % args.video)
    print('  duration  : %.2f s' % duration)
    print('  sampled   : %d frames @ %.1f fps' % (count, args.fps))
    print('  darkest   : t=%ss  mean=%s  edges=%s' % worst)
    print()

    if empties:
        print('  EMPTY FRAMES (%d):' % len(empties))
        for t, mean, edges in empties[:40]:
            print('    t=%-7s mean=%-7s edges=%s' % (t, mean, edges))
        if len(empties) > 40:
            print('    ... and %d more' % (len(empties) - 40))
        print()
        print('  FAIL')
        return 1

    print('  no empty frames')

    # Motion: is anything actually moving? A promo for a moving wallpaper once
    # rendered with a frozen one and passed every other check, because the frames
    # had content - it just never changed.
    print()
    print('  motion (whole frame):')
    still = 0
    changes = []
    for i in range(1, count):
        a = raw[(i - 1) * size:i * size]
        b = raw[i * size:(i + 1) * size]
        d = sum(abs(a[j] - b[j]) for j in range(0, size, 7)) / (size // 7)
        changes.append(d)
        if d < 0.05:
            still += 1
    if changes:
        avg = sum(changes) / len(changes)
        print('    average change between sampled frames: %.2f' % avg)
        print('    frames with no change at all        : %d/%d' % (still, len(changes)))
        if still > len(changes) * 0.5:
            print('    WARNING: more than half the frames are identical -')
            print('             the video may contain long static holds.')
    if args.expect is not None and abs(duration - args.expect) > 0.5:
        print('  duration mismatch: expected %.2fs, got %.2fs' % (args.expect, duration))
        print('  FAIL')
        return 1
    print('  PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
