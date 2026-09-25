# Design notes

The design follows xinet.id, the rest of the group, so LumaWall reads as part of
the same family rather than a separate product. This file records what that means
in practice, and what was removed to get there.

## Type

**Plus Jakarta Sans**, the same family xinet.id uses. One family for everything:
headlines, body, labels, numbers.

The earlier version used Bahnschrift for headings and Cascadia Mono for labels and
figures. The monospace labels were the single biggest contributor to a
"generated" look — a technical-looking font used for decoration rather than for
code.

Self-hosted from `site/assets/fonts/` as a variable font, so one 27 KB file covers
weights 200–800. Served from our own domain rather than Google's, so there is no
third-party request and the type works offline.

## Colour

One accent: the product's crimson `#ff3b57`, used for the primary action and a
single highlight per screen.

The earlier version also had a cyan secondary, gradient text, and coloured glows
on hover states. Each is defensible alone; together they competed for attention
and made the page feel restless.

Contrast against the page background is verified: body text 18.45:1, muted text
6.96:1, accent 5.68:1 — all above the WCAG AA threshold of 4.5:1.

## Motion

One animation, used everywhere: a 1.8 s rise with a blur that clears, easing on
`cubic-bezier(.16, 1, .3, 1)`. That is the animation xinet.id uses.

Removed: per-character headline reveals, count-up numbers, a shiny sweep across
labels, hover lifts on cards, and staggered cascades. Every one of those was
removed for the same reason — the page had six things moving at once, which reads
as decoration rather than design.

The reveal is applied by script, never in the base stylesheet, so with JavaScript
off nothing is hidden.

## The promo video

Rendered from React source in `promo/`. The renderer drives a deterministic clock
and captures each frame through the Chrome DevTools Protocol, so a re-run produces
the same video.

### It is one continuous camera move, not a slideshow

The earlier version cut between scenes: each one faded in, held still, then faded
out. That is a slideshow, and no amount of polish on individual frames changes
what it is.

Now there is a single camera for all 52 seconds and it never stops: a slow push
in, a sideways drift, a fraction of a degree of roll. The beats sit along the
camera's path and the camera travels past them, so a transition is the camera
arriving somewhere new rather than one picture replacing another. Layers at
different depths move by different amounts, which is what gives a flat composition
the sense of having depth.

### The handover is a pan, not a crossfade

A crossfade always has a moment where both beats are semi-visible, and a review of
an earlier render picked that exact frame out: two headings at half strength, one
behind the other. Even with the opacities summing to exactly 1 it reads as a
mistake, because the eye sees two things in the same place.

So there is no crossfade at all. Both beats stay fully opaque and the frame pans:
the outgoing one travels a full frame width to the left while the incoming one
arrives from the right. At any instant you see the tail of one and the head of the
other, side by side and moving the same way, which is what a camera moving past a
boundary looks like. Their separation is the frame width at every instant, so no
text can ever sit on top of other text.

The same idea applies inside a beat: the scene's own wallpaper slides at 40% of
the distance and its content at 100%, so the handover has two planes rather than
reading as one sheet of paper moving.

There was also a double scale. Each beat used to scale from 0.965 to 1 while the
camera was scaling the whole frame at a different rate, so every handover zoomed
twice. That was the "weird zoom" in the transitions; it is gone.

### The wallpaper actually moves

This was the real failure: the promo for a moving wallpaper contained still
screenshots of one.

Two causes, both silent:

1. **The wallpaper was a `<video>`.** A video element plays from the wall clock.
   During a frame-by-frame render the browser advances it independently of the
   renderer, so its content is random per frame and the same frame can be captured
   twice. The clips are now pre-extracted to image sequences
   (`tools/extract-clips.py`) and the component picks
   `frames[floor(t * fps) % count]`, making the position an exact function of the
   render time.

2. **Aurora painted an opaque background.** Every scene placed its wallpaper
   first and then rendered `Aurora` on top, which filled the frame with a solid
   gradient. The wallpaper was there the whole time and completely invisible. It
   is now a tint at low alpha.

Both are guarded now: `render.mjs` refuses to render if any wallpaper frame fails
to load, and `tools/check_frames.py` reports whether the video actually moves.

### The hero image is composed for the hero

The hero was a wallpaper forced into a wide band with `object-fit: cover`, which
sliced the top of the character's head off and pushed her against the right edge.
`object-position` can only choose which arbitrary point of the source survives; it
cannot move the subject somewhere better, and it cannot darken one side for the
type while leaving the other bright.

`tools/make-hero-image.py` composes an image for the slot instead: subject in the
right third, clear of the headline, with a smooth left-to-right ramp to near-black
so the text has a surface. The ramp is a `geq` alpha curve, not a `drawbox` — a box
left a visible vertical seam down the middle of the artwork.

### The promo video plays itself, and stops when told to

It starts when the block reaches the viewport and pauses when it leaves, so a
visitor sees it from the beginning rather than arriving twenty seconds in.

A deliberate pause is respected. If the visitor presses pause, scrolling away and
back does not restart it — a page that overrides that is a page that fights its
user. `tools/check-page.mjs` tests exactly this, because the regression is
invisible otherwise: the video plays either way and only the visitor's intent is
lost.

There is no play cover and no resolution badge. The cover existed to work around a
video that did not start on its own; with autoplay working it was a button that
hid the thing it was advertising. The badge labelled a technical detail the viewer
does not choose between.

### Verifying a render

```
cd promo
node render.mjs --duration 52 --crf 19 --out ../site/assets/video/lumawall-promo.mp4

cd ..
python tools/check_frames.py site/assets/video/lumawall-promo.mp4 --expect 52
node tools/verify-live.mjs
```

`check_frames.py` reports empty frames and the average change between sampled
frames. A video whose wallpaper is frozen passes the empty-frame test — the frames
have content, it just never changes — which is how the earlier version shipped.

## Files

| path | role |
|---|---|
| `promo/src/anim.js` | easings, the camera, parallax |
| `promo/src/WallpaperStage.jsx` | plays a wallpaper from its frame sequence |
| `promo/src/Timeline.jsx` | the camera and the beat windows |
| `promo/frames/` | render-only frame sequences (13 MB, never deployed) |
| `tools/extract-clips.py` | extracts the sequences from the wallpaper library |
| `promo/render.mjs` | drives the clock, captures frames, encodes |
