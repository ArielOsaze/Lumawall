"""Final verification of the artefacts that shipped.

Checks the committed promo video for empty frames and every committed
screenshot for actual content, so a black or corrupted image can never reach
the live site unnoticed.
"""

import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
# The script lives in tools/, so the repository root is one level up. Resolve it
# rather than assuming the caller's working directory.
if os.path.basename(ROOT) == "tools":
    ROOT = os.path.dirname(ROOT)
VIDEO = os.path.join(ROOT, "site", "assets", "video", "lumawall-promo.mp4")
SHOTS = os.path.join(ROOT, "site", "assets", "shots")
TMP = os.path.join(ROOT, "build", "final-verify")


def frame_deviation(path):
    """Count pixels that differ from their row median.

    The background is a smooth gradient, so any real content (text, panels,
    cards) shows up as pixels far from the row's median. A blank frame has
    almost none.
    """
    im = Image.open(path).convert("RGB").resize((240, 135))
    px = im.load()
    dev = 0
    for y in range(135):
        row = [sum(px[x, y]) for x in range(240)]
        median = sorted(row)[120]
        dev += sum(1 for v in row if abs(v - median) > 34)
    return dev


def check_video():
    if not os.path.exists(VIDEO):
        print("  VIDEO MISSING:", VIDEO)
        return False
    size = os.path.getsize(VIDEO) / 1048576
    print("FINAL VIDEO  (%.2f MB)" % size)

    os.makedirs(TMP, exist_ok=True)
    tmp_frame = os.path.join(TMP, "f.png")

    bad = []
    times = [x / 10 for x in range(0, 521, 2)]  # every 0.2 s
    for t in times:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", VIDEO,
             "-frames:v", "1", tmp_frame, "-y"],
            check=True)
        dev = frame_deviation(tmp_frame)
        if dev < 60:
            bad.append((t, dev))

    print("  sampled %d frames (every 0.2s)" % len(times))
    if bad:
        print("  LOW-CONTENT FRAMES:")
        for t, d in bad:
            print("    t=%.1f  deviating=%d" % (t, d))
        return False
    print("  every sampled frame contains content")
    return True


def check_shots():
    print()
    print("COMMITTED SCREENSHOTS")
    ok = True
    for name in sorted(os.listdir(SHOTS)):
        path = os.path.join(SHOTS, name)
        if not name.lower().endswith(".png"):
            continue
        im = Image.open(path).convert("RGB")
        small = im.resize((160, 90))
        px = small.load()
        luma = sum(sum(px[x, y]) for y in range(90) for x in range(160)) / (160 * 90)
        # Structure, not brightness: this is a dark UI whose content is mostly
        # text, so variance alone flags good screenshots. Edge density (how many
        # neighbouring pixels differ) is near zero for a black or corrupted
        # capture and clearly positive for any real interface.
        grey = im.convert("L").resize((320, 180))
        px = grey.load()
        edges = 0
        for y in range(1, 179):
            for x in range(1, 319):
                if abs(px[x, y] - px[x - 1, y]) > 14 or abs(px[x, y] - px[x, y - 1]) > 14:
                    edges += 1
        density = 100.0 * edges / (319 * 179)
        verdict = "OK" if (luma > 10 and density > 1.5) else "SUSPECT"
        if verdict != "OK":
            ok = False
        print("  %-24s %sx%-5s luma %5.1f  edge density %5.1f%%  %s"
              % (name, im.width, im.height, luma, density, verdict))
    return ok


def main():
    video_ok = check_video()
    shots_ok = check_shots()
    print()
    if video_ok and shots_ok:
        print("ALL ARTEFACTS VERIFIED")
        return 0
    print("PROBLEMS FOUND")
    return 1


if __name__ == "__main__":
    sys.exit(main())
