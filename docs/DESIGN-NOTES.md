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
