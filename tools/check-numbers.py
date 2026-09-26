"""check-numbers.py — is any invalid value drawn as text in the promo?

Why this exists:

The finished render once showed "NaN%" where "60%" and "11%" belong, in the CPU
comparison - the piece's central claim. It survived every check that was running,
because none of them asked whether the figures on screen were valid: the frame was the
right size, the text was legible, every scene was present, and NaN is perfectly legible
text. The cause was one property read off the wrong object, which made a scene's time
undefined and every derived number NaN.

── why this reads the DOM and not the pixels ───────────────────────────────

The first four versions of this check tried to find the shape of "NaN" in the rendered
video, and every one of them failed on real frames:

  1. Three equal-width glyphs in a short line. That is what NaN looks like - N, a and N
     in different cases, the same advance width. It reported the word "sama" at 30.0s:
     three glyphs, near-equal width, a compact mark after them, short for their height.
     Every condition was satisfied by a word.

  2. Require the following glyph to be markedly narrower, reasoning that a percent sign
     is narrower than a letter. The full stop after "sama" is narrower too.

  3. Require the follower to be a percent sign by vertical position - its dot sits high
     where a full stop sits on the baseline. True, and fragile: a lowercase "i" has a
     high tittle too, and this leans on rendering details a font change would break.

  4. Count digits in every value-shaped run. This reported the orange badge dot in
     `pause`, the small print in `apply` and the link text in `close`, and each one
     would have needed its own size threshold. Worse, the first version of it accepted
     only 3-4 glyphs per figure, so "41.2%" - five glyphs - was never examined at all
     while the check reported a pass.

All four were trying to read text from pixels. But the text is not in the pixels - it is
in the scene, and the renderer computes it from JavaScript. So this asks the scene
directly: promo/numbers-probe.mjs renders every scene at five moments and reads back
every string of text in the DOM, plus every number inside a transform.

That is exact. A "NaN" cannot hide from it, and a word cannot be mistaken for one.

It also checks the positive: the figures that MUST appear are confirmed to be there,
because a missing number and an invalid number are different bugs with the same symptom.

Usage:
    python tools/check-numbers.py
"""

import json
import os
import subprocess
import sys

PROBE = 'promo/numbers-probe.mjs'

# The values that must appear somewhere in the piece, with the scene that draws them.
# These are the claims the promo makes; if one silently becomes a zero or an empty
# string the piece still renders and still passes every other check.
REQUIRED = {
    'perf':    ['41.2%', '2.4%'],
    'problem': ['40.9%'],
    'quality': ['3840×2160'],
}

INVALID = ('NaN', 'undefined', 'Infinity', 'null')


def main():
    print()
    print('  numbers: does every figure on screen come out as a real number?')
    print()

    if not os.path.exists(PROBE):
        print('  %s is missing' % PROBE)
        return 1

    r = subprocess.run(['node', 'numbers-probe.mjs'], capture_output=True, text=True,
                       timeout=300, cwd='promo')
    if r.returncode != 0 or not r.stdout.strip():
        print('  could not render the scenes:')
        print('    %s' % (r.stderr or r.stdout or '')[:400])
        return 1

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        print('  the probe did not return JSON')
        print('    %s' % r.stdout[:400])
        return 1

    results = data['results']
    print('    %d scene samples rendered (every scene, five moments each)' % len(results))

    problems = []

    # ── 1. no invalid value, in text or in a transform ───────────────────────
    bad = []
    for r_ in results:
        if r_.get('error'):
            problems.append('%s at %.2fs threw: %s' % (r_['id'], r_['t'], r_['error']))
            continue
        for s in r_.get('text', []):
            if any(k in s for k in INVALID):
                bad.append((r_['id'], r_['t'], s))
        for s in r_.get('styleNums', []):
            if any(k in s for k in INVALID):
                bad.append((r_['id'], r_['t'], 'transform: ' + s))

    print()
    if bad:
        print('    INVALID VALUES ON SCREEN: %d' % len(bad))
        for i, t, s in bad[:12]:
            print('      %-9s t=%-5.2f  %s' % (i, t, s[:80]))
        problems.append('%d invalid values are drawn as text' % len(bad))
    else:
        print('    no NaN, undefined, Infinity or null in any text or transform')

    # ── 2. the claims are present ────────────────────────────────────────────
    by_scene = {}
    for r_ in results:
        by_scene.setdefault(r_['id'], []).extend(r_.get('text', []))

    print()
    print('    the figures the piece claims:')
    for scene, wanted in REQUIRED.items():
        texts = by_scene.get(scene, [])
        for w in wanted:
            # The figure is drawn by a count-up, so it appears at several intermediate
            # values through the shot; the final value is the one that must be present.
            ok = any(w in t for t in texts)
            print('      %-9s %-14s %s' % (scene, w, 'ok' if ok else 'MISSING'))
            if not ok:
                problems.append('%s never draws %s' % (scene, w))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        print()
        print('  A value that fails to compute is drawn as "NaN", and a value that is')
        print('  never reached is simply absent. Both render perfectly.')
        return 1

    print('  every figure on screen is a real number, and every claim is present')
    return 0


if __name__ == '__main__':
    sys.exit(main())
