// Direction.jsx — how the piece moves: hard cuts on motion, one camera per shot.
//
// ── what was wrong with every earlier version ───────────────────────────────
//
// Four rounds went into the transitions: crossfade, then a slide, then a slide with
// blur, then a blur derived from the velocity. The note that kept coming back was
// still "like a PowerPoint", and each round assumed the join was the problem.
//
// The join was never the problem. Two things were:
//
//   1. THE TRANSITIONS WERE VISIBLE AT ALL. A crossfade, a push, a wipe - anything
//      the eye can watch happening is a transition effect, and transition effects
//      are what presentation software has. Professional work does not animate
//      between shots. It CUTS, and the cut lands on movement so the eye follows the
//      motion instead of noticing the join.
//
//   2. EVERY SHOT WAS THE SAME SHAPE. Headline on the left, picture on the right,
//      seven times. That is a slide template. It does not matter how good the
//      seventh one is if it is laid out like the first.
//
// So this file does the opposite of what the earlier ones did:
//
//   · Shots cut. There is no crossfade, no push, no wipe, and nothing travels
//     between two shots. Each shot starts already in motion.
//   · A cut gets a 5-frame directional smear that peaks ON the cut frame. That is
//     the one transition technique here, it is what a whip-pan cut is, and it lasts
//     0.17s - short enough that it reads as the camera moving rather than as an
//     effect playing.
//   · Shots are timed unevenly and are not all the same length.
//
// ── why this revision has eleven shots and no repeats ──────────────────────
//
// The previous revision answered "it still looks like slides" by cutting the same
// seven scenes twice as fast - thirteen shots, but only seven ideas, and the second
// half was the first half again with a different wallpaper. A review caught it:
// "the frame at 0-3s is repeated at 24-27s and 50-51s". Halving the shot length does
// not add anything to watch if the content is a repeat.
//
// So this version has ELEVEN distinct scenes and no scene appears twice. It is
// slightly shorter, and every second of it is new. Two of the eleven did not exist
// before: the pipeline scene, which draws the GPU path rather than claiming it, and
// the quality scene, which shows a file going through untouched.
//
// The shot lengths are set by what each scene has to do, not by a target average:
// the pipeline and the measured comparison need longer to be read, the wall of
// previews is a mood and can be shorter.

import { clamp01, lerp, seg, easeInOut, easeOut, easeOutQuint } from './anim.js';

export const TOTAL_SECONDS = 46.4;
export const FPS = 30;
export const FRAME_W = 1920;
export const FRAME_H = 1080;

// ── the shots ────────────────────────────────────────────────────────────────
//
// `cut` is when the shot begins. The end of a shot is the next shot's cut, so the
// list is a sequence of hard boundaries - there is nothing between them.
export const SHOTS = [
  { id: 'hook',     cut: 0.0 },    // 4.0s  the product, playing
  { id: 'problem',  cut: 4.0 },    // 4.0s  what it usually costs
  { id: 'browse',   cut: 8.0 },    // 4.0s  the catalogue, being used
  { id: 'apply',    cut: 12.0 },   // 3.8s  pick it, and it lands
  { id: 'multi',    cut: 15.8 },   // 4.2s  one screen at a time
  { id: 'pause',    cut: 20.0 },   // 4.0s  stopping it without closing it
  { id: 'gpu',      cut: 24.0 },   // 4.8s  the pipeline
  { id: 'perf',     cut: 28.8 },   // 4.4s  the measurement
  { id: 'quality',  cut: 33.2 },   // 4.2s  the file, untouched
  { id: 'library',  cut: 37.4 },   // 4.0s  the scale of it
  { id: 'close',    cut: 41.4 },   // 5.0s  the mark and where to get it
];

/** Which shot is on screen at time t, and how long it has been running. */
export function shotAt(t) {
  let i = 0;
  for (let k = 0; k < SHOTS.length; k++) {
    if (t >= SHOTS[k].cut) i = k;
  }
  // `cut` is returned as well as `local`, because a scene needs both: its own
  // elapsed time for its animation, and the moment it began for anything that has
  // to know where it sits in the piece.
  return { index: i, id: SHOTS[i].id, cut: SHOTS[i].cut, local: t - SHOTS[i].cut };
}

/**
 * The whip that hides a cut.
 *
 * Returns 0..1, peaking exactly on the cut frame. The smear is asymmetric on
 * purpose: it starts a frame or two before the cut and clears quickly after it,
 * because the incoming shot has to be readable almost immediately. A symmetric
 * envelope spends as long dissolving into the new shot as it did leaving the old
 * one, which is a crossfade again.
 */
export function cutWhip(t, window = 0.17) {
  const before = window * 0.35;
  const after = window * 0.65;

  for (let i = 1; i < SHOTS.length; i++) {
    const c = SHOTS[i].cut;
    if (t >= c - before && t <= c + after) {
      // 0 at the edges, 1 at the cut. The rise is linear and the fall is eased, so
      // the smear is gone quickly once the new shot is in.
      if (t <= c) return clamp01((t - (c - before)) / before);
      return 1 - easeOut((t - c) / after);
    }
  }
  return 0;
}

/** The direction the whip travels, alternating so the cuts do not all go one way. */
export function cutAngle(t) {
  for (let i = 1; i < SHOTS.length; i++) {
    if (t >= SHOTS[i].cut - 0.17 && t <= SHOTS[i].cut + 0.17) {
      // Alternating, with a slight diagonal so it never reads as a horizontal
      // wipe - which is the one direction that does look like presentation
      // software.
      const dir = i % 2 === 1 ? 1 : -1;
      return dir * (18 + (i % 3) * 9);
    }
  }
  return 0;
}

/**
 * The camera for the whole piece.
 *
 * One continuous move from the first frame to the last, never reset. It pushes in
 * slowly and drifts, so no shot is ever a still image - which is the other half of
 * not looking like a deck. A slide can be static; a camera cannot.
 */
export function camera(t) {
  const { index, local } = shotAt(t);
  const next = SHOTS[index + 1];
  const shotLen = next ? next.cut - SHOTS[index].cut : TOTAL_SECONDS - SHOTS[index].cut;

  // A global push, so the frame is always creeping forward.
  const p = clamp01(t / TOTAL_SECONDS);
  const globalZ = 1 + 0.075 * p;

  // A per-shot push, sized to the SHOT rather than to a fixed duration. Tying it to
  // the shot's own length means every shot completes its push whatever length it is.
  const shotZ = 1 + 0.10 * easeOutQuint(clamp01(local / Math.max(1.2, shotLen * 0.8)));

  // Drift, phase-locked to absolute time so it is reproducible.
  const x = Math.sin(t * 0.44) * 28 + Math.sin(t * 0.15) * 12;
  const y = Math.cos(t * 0.51) * 18 - Math.sin(t * 0.22) * 8;

  // A roll of a fraction of a degree: enough that the frame feels hand-held,
  // never enough to read as a tilt.
  const roll = Math.sin(t * 0.27) * 0.26;

  return { z: globalZ * shotZ, x, y, roll, index, local, shotLen };
}

/** The camera's CSS transform. */
export function cameraTransform(t) {
  const c = camera(t);
  return (
    `translate3d(${c.x.toFixed(2)}px, ${c.y.toFixed(2)}px, 0) ` +
    `scale(${c.z.toFixed(4)}) rotate(${c.roll.toFixed(3)}deg)`
  );
}

/**
 * Motion blur radius in pixels, from the camera's own speed.
 *
 * A blur has to follow how far the content actually moves between two captured
 * frames or it reads as two half-scenes instead of one smear.
 */
export function motionBlur(t, fps = FPS) {
  // How fast the push is moving, in screen pixels per frame, near the frame edge.
  const dz = (camera(t + 1 / fps).z - camera(t).z) * (FRAME_W / 2);
  // And how far the drift moves the frame.
  const dx = (camera(t + 1 / fps).x - camera(t).x);
  const dy = (camera(t + 1 / fps).y - camera(t).y);
  const perFrame = Math.hypot(dx, dy) + Math.abs(dz) * 0.5;
  return Math.min(10, perFrame * 0.6);
}

/**
 * The shot's own presence: how much of it is on screen.
 *
 * A hard cut means 0 or 1 - there is no in-between - and that is the point. The
 * value exists so a shot can be culled when it is not the current one, not so it
 * can be faded.
 */
export function presence(shot, t) {
  const { id } = shotAt(t);
  return id === shot.id ? 1 : 0;
}

/** Progress through the shot, 0 at the cut and 1 at the next one. */
export function shotProgress(t) {
  const { index, local } = shotAt(t);
  const next = SHOTS[index + 1];
  if (!next) return clamp01(local / (TOTAL_SECONDS - SHOTS[index].cut));
  return clamp01(local / (next.cut - SHOTS[index].cut));
}

export { clamp01, lerp, seg, easeInOut, easeOut, easeOutQuint };
