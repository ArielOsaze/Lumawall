# What changed, and how each one is verified

Every item below was a request, and each has a check that fails if it regresses.
`python tools/verify-all.py` runs them all.

## The promo video

**It was a slideshow.** The earlier version cut between scenes: each faded in,
held still, faded out. No amount of polish on individual frames changes what that
is.

Now there is one camera for all 52 seconds and it never stops. Beats sit along its
path and it travels past them, so a transition is the camera arriving somewhere
new.

**The wallpaper did not move**, in a promo for a moving wallpaper. Two causes,
both silent: the wallpaper was a `<video>` element, which plays from the wall
clock and so produces random content per rendered frame; and `Aurora` painted an
opaque background over every scene's wallpaper. The clips are now pre-extracted
image sequences driven by the render clock, and Aurora is a tint.

*Verified by* `check-promo-scenes.py` (a wallpaper visible in every beat) and
`check_frames.py` (no frozen frames — a frozen wallpaper passes an emptiness test).

**The transitions had a zoom and an overlap.** Two separate defects:

- Each beat scaled 0.965 → 1 while the camera scaled the whole frame at a
  different rate, so every handover zoomed twice. That was the "weird zoom".
- The incoming beat finished fading in over 0.75s while the crossfade ran for
  1.6s, so for about 0.7s both beats sat near full opacity: two headings and two
  sets of figures overlapping.

A crossfade always has that moment, even with the opacities summing to 1, so there
is no crossfade at all. Both beats stay fully opaque and the frame pans a full
width: the outgoing one travels left while the incoming one arrives from the
right. Their separation is the frame width at every instant.

*Verified by* `check-transition-curve.py`, which mirrors the arithmetic and
asserts the separation.

## The website

**Autoplay.** The video starts when the block reaches the viewport and pauses when
it leaves, so a visitor sees it from the beginning rather than arriving twenty
seconds in. A deliberate pause survives scrolling away and back.

*Verified by* `check-page.mjs` on the local copy and
`verify-live-behaviour.mjs` on the deployed domain — the regression is invisible
otherwise, because the video plays either way and only the visitor's intent is
lost.

**The 1080p badge is gone**, along with the play cover. The cover existed to work
around a video that did not start on its own; with autoplay working it was a
button hiding the thing it advertised.

**The hero was badly cropped.** A portrait wallpaper forced into a wide band
sliced the subject's head off. `object-position` can only choose which arbitrary
point survives; it cannot move the subject somewhere better. `make-hero-image.py`
now composes an image for the slot: subject right, a smooth left-to-right ramp to
near-black for the type. The ramp is a `geq` alpha curve because a `drawbox` left
a visible seam.

*Verified by* `check-responsive.mjs` at 1366×768, 1440×900, 2560×1080 and
390×844.

**The copy read as machine-written.** Not vocabulary — structure. Three headings
shared the "X, bukan Y" shape; two asked questions the page then answered; the
tagline named a category instead of making a promise. Em-dashes as dramatic
pauses, "bukan sekadar", "yang memang", "tanpa perlu" and one tricolon were
removed throughout.

*Verified by* `check-copy.py` for the site and the promo, `check-app-text.py` for
the app's own 349 strings.

## How to check it yourself

```
python tools/verify-all.py          # everything, one table
node   tools/verify-live-behaviour.mjs   # the deployed site
python tools/check-promo-scenes.py site/assets/video/lumawall-promo.mp4
```

## Still open

- **MSIX identity.** `AppIdentity` still reads `Name="LumaWall.DesktopEngine"` and
  `Publisher="CN=LumaWall"`. Those must be the exact values Partner Center issues;
  they cannot be guessed, and the package will not be accepted without them.
- **CDN cache.** Assets are served with `max-age=86400`. A visitor who loaded the
  site before a deploy may see the old version until it expires.
