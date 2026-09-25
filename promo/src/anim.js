// anim.js — pure easing and interpolation helpers.
//
// Why everything is a pure function of time:
//
// Animation libraries drive their animations from the wall clock. That is right
// for a website and wrong for a video: if the renderer asks for frame 200, the
// library has no way to know that - it only knows how long it has been running,
// so the same frame number produces a different image on every run.
//
// Here every animated value is computed from the scene's time offset, so frame N
// always produces exactly the same pixels. A re-render is byte-comparable.

export const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

/** Progress of a segment: 0 before `from`, 1 after `to`. */
export function seg(t, from, to) {
  if (to === from) return t >= to ? 1 : 0;
  return clamp01((t - from) / (to - from));
}

/** Linear interpolation. */
export const lerp = (a, b, k) => a + (b - a) * k;

/** Map a 0..1 progress onto a range. */
export const range = (k, a, b) => lerp(a, b, k);

// ── easings ─────────────────────────────────────────────────────────────────
export const easeOut = (k) => 1 - Math.pow(1 - k, 3);
export const easeOutExpo = (k) => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k));
export const easeOutBack = (k, s = 1.7) => {
  const c = s + 1;
  return 1 + c * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
};
export const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
export const easeIn = (k) => k * k * k;

/** Animate a value with an easing, over a time window. */
export function anim(t, from, to, start, end, easing = easeOut) {
  return lerp(from, to, easing(seg(t, start, end)));
}

/** A value that rises then falls - useful for one-shot pulses. */
export function pulse(t, start, dur) {
  const k = seg(t, start, start + dur);
  return Math.sin(k * Math.PI);
}

/** Spring-ish settle: overshoots slightly then comes back. */
export function spring(t, start, dur, overshoot = 1.06) {
  const k = seg(t, start, start + dur);
  if (k >= 1) return 1;
  const e = easeOutBack(k, (overshoot - 1) * 12);
  return e;
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
