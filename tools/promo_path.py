"""promo_path.py — finds the promo video, whatever hash its filename carries.

The asset URLs carry a content hash now (lumawall-promo.c438ada022.mp4) so a browser
cannot serve a week-old copy. That broke every tool that hard-coded the plain name:
five checks in verify-all reported "no video at site/assets/video/lumawall-promo.mp4"
against a perfectly good render.

Rather than update each call site with a pattern, the lookup lives here: a tool asks
for "the promo" and gets whichever file exists, plain name or hashed.
"""

import glob
import os
import re

SITE = 'site'


def promo_video(site=SITE):
    """The promo video's path, hashed or not, or None."""
    folder = os.path.join(site, 'assets', 'video')
    if not os.path.isdir(folder):
        return None

    # Prefer the hashed form - that is the one the page references.
    hashed = sorted(glob.glob(os.path.join(folder, 'lumawall-promo.*.mp4')))
    hashed = [h for h in hashed if not h.endswith('.part.mp4')]
    if hashed:
        # If several exist, take the newest.
        return max(hashed, key=os.path.getmtime)

    plain = os.path.join(folder, 'lumawall-promo.mp4')
    return plain if os.path.exists(plain) else None


def hero_video(site=SITE):
    """The hero loop's path, hashed or not, or None."""
    folder = os.path.join(site, 'assets', 'video')
    if not os.path.isdir(folder):
        return None
    hashed = sorted(glob.glob(os.path.join(folder, 'hero-loop.*.mp4')))
    if hashed:
        return max(hashed, key=os.path.getmtime)
    plain = os.path.join(folder, 'hero-loop.mp4')
    return plain if os.path.exists(plain) else None


def asset(site, rel):
    """Resolve 'assets/video/x.mp4' to a real file, trying the hashed form.

    Returns the path on disk, or None. Used by tools that are given a logical asset
    name and have to find its current versioned filename.
    """
    direct = os.path.join(site, rel)
    if os.path.exists(direct):
        return direct

    folder, name = os.path.split(rel)
    stem, ext = os.path.splitext(name)
    folder_path = os.path.join(site, folder)
    if not os.path.isdir(folder_path):
        return None

    pattern = re.compile(re.escape(stem) + r'\.[0-9a-f]{6,}\.' + re.escape(ext.lstrip('.')) + '$')
    found = [f for f in os.listdir(folder_path) if pattern.fullmatch(f)]
    if not found:
        return None
    return os.path.join(folder_path, max(found, key=lambda f: os.path.getmtime(os.path.join(folder_path, f))))


if __name__ == '__main__':
    p = promo_video()
    h = hero_video()
    print('  promo: %s' % (p or 'NOT FOUND'))
    print('  hero : %s' % (h or 'NOT FOUND'))
