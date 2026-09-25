// anim.js — pure easing, interpolation, and the camera.
//
// Every animated value in the promo is a pure function of time, so frame N
// always produces exactly the same pixels and a re-run is byte-comparable.
//
// Animation libraries drive from the wall clock, which is right for a website
// and wrong for a video: the renderer asks for frame 200, the library only knows
// how long it has been running, so the same frame number produces a different
// image on every run.

export const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

/** Progress of a segment: 0 before `from`, 1 after `to`. */
export function seg(t, from, to) {
  if (to === from) return t >= to ? 1 : 0;
  return clamp01((t - from) / (to - from));
}

export const lerp = (a, b, k) => a + (b - a) * k;
export const range = (k, a, b) => lerp(a, b, k);

// ── easings ─────────────────────────────────────────────────────────────────
export const easeOut = (k) => 1 - Math.pow(1 - k, 3);
export const easeOutQuint = (k) => 1 - Math.pow(1 - k, 5);
export const easeOutExpo = (k) => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k));
export const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
export const easeIn = (k) => k * k * k;
export const easeOutBack = (k, s = 1.7) => {
  const c = s + 1;
  return 1 + c * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
};

/** Animate a value with an easing, over a time window. */
export function anim(t, from, to, start, end, easing = easeOut) {
  return lerp(from, to, easing(seg(t, start, end)));
}

/** A value that rises then falls — useful for one-shot pulses. */
export function pulse(t, start, dur) {
  return Math.sin(seg(t, start, start + dur) * Math.PI);
}

/** Spring-ish settle: overshoots slightly then comes back. */
export function spring(t, start, dur, overshoot = 1.06) {
  const k = seg(t, start, start + dur);
  if (k >= 1) return 1;
  return easeOutBack(k, (overshoot - 1) * 12);
}

/** A looping value, phase-locked to absolute time so it is reproducible. */
export function loop(t, period, phase = 0) {
  return ((t / period + phase) % 1 + 1) % 1;
}

/** Deterministic pseudo-random in [0,1) from an integer seed. */
export function rand(seed) {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/* ───────────────────────────────────────────────────────────────────────────
   The camera.

   The previous version of this promo cut between scenes: each one faded in,
   held still, then faded out. That is a slideshow, and it is why it read as a
   PowerPoint deck however clean the individual frames were.

   A continuous piece moves instead. There is one camera for the whole video and
   it never stops: it pushes in, drifts sideways, and carries a slow roll the
   entire time. Scenes live in the camera's world and the camera travels past
   them, so a transition is the camera moving from one to the next rather than
   one picture replacing another.
   ─────────────────────────────────────────────────────────────────────────── */

/**
 * Camera state at time `t`.
 *
 * `z` is the push. It grows steadily across the whole video so the frame is
 * always creeping forward, with a gentle sway on top so the speed is not
 * mechanically constant. `x` and `y` are a slow drift, and `roll` is a fraction
 * of a degree — enough to feel alive, never enough to read as a tilt.
 */
export function camera(t, total) {
  const p = clamp01(t / total);

  return {
    z: 1 + 0.10 * p + 0.012 * Math.sin(t * 0.21),
    x: Math.sin(t * 0.13) * 26 + p * 18,
    y: Math.cos(t * 0.17) * 18 - p * 10,
    roll: Math.sin(t * 0.09) * 0.22,
  };
}

/** The camera's CSS transform at a given time. */
export function cameraTransform(t, total, extra = 1) {
  const c = camera(t, total);
  return `translate3d(${c.x}px, ${c.y}px, 0) scale(${c.z * extra}) rotate(${c.roll}deg)`;
}

/**
 * Offset for a layer at a given depth.
 *
 * Nearer layers move more than distant ones, which is what makes a flat
 * composition read as having depth. `depth` 0 pins a layer to the camera; 1 is
 * the nearest plane.
 */
export function parallax(t, total, depth, amp = 40) {
  const c = camera(t, total);
  const k = (depth * amp) / 40;
  return {
    x: c.x * k,
    y: c.y * k,
    scale: 1 + (c.z - 1) * depth,
  };
}
