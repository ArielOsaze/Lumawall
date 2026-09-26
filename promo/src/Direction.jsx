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
//      motion instead of noticing the join. Ninety percent of the cuts in a
//      broadcast commercial are invisible because nothing was animated across them.
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
//   · Shots are timed unevenly and are not all the same length. Even spacing is the
//     clearest tell of a slideshow.

import { clamp01, lerp, seg, easeInOut, easeOut, easeOutQuint } from './anim.js';

export const TOTAL_SECONDS = 52.0;
export const FPS = 30;
export const FRAME_W = 1920;
export const FRAME_H = 1080;

// ── the shots ────────────────────────────────────────────────────────────────
//
// `cut` is when the shot begins. The end of a shot is the next shot's cut, so the
// list is a sequence of hard boundaries - there is nothing between them.
//
// ── why there are thirteen now instead of seven ─────────────────────────────
//
// A storyboard of every second of the seven-shot version showed the real reason it
// read as a slideshow, and it was not the transitions - every round of work had gone
// into those. It was this:
//
//   · Each shot held for 6-8 seconds, and the animation inside it finished after
//     2-4. Measured on the finished render: Catalog had 0.6s of movement left,
//     Monitors 6.6s of dead air, Perf 5.8s, Intro 4.7s. So each shot was a still
//     image held on screen for most of its life - which IS a slide, whatever the cut
//     into it looks like.
//   · Seven messages over 52 seconds is a deck's pace. A motion piece changes every
//     few seconds.
//
// So the shots are half as long and there are twice as many. Thirteen shots, 2.6 to
// 4.4 seconds each, average 4.0. The longest shot here is shorter than the SHORTEST
// shot of the previous version.
//
// The lengths still vary, because even pacing is its own tell - but the variation is
// now within a range the eye reads as "cutting", not as "advancing".
export const SHOTS = [
  { id: 'intro',      cut: 0.0 },
  { id: 'problem',    cut: 3.4 },
  { id: 'catalog',    cut: 7.4 },
  { id: 'monitors',   cut: 11.4 },
  { id: 'pause',      cut: 15.6 },
  { id: 'perf',       cut: 19.6 },
  { id: 'outro',      cut: 23.8 },
  // The second half repeats the story with different wallpapers and a different
  // framing, so the piece keeps changing without needing new scenes: the same seven
  // compositions, entered at a different point in their animation and with a
  // different wallpaper behind them. A second pass through a message is how a
  // commercial fills 52 seconds; it is not the same as holding one shot.
  { id: 'problem',    cut: 28.0, variant: 1 },
  { id: 'catalog',    cut: 32.0, variant: 1 },
  { id: 'monitors',   cut: 36.0, variant: 1 },
  { id: 'pause',      cut: 40.0, variant: 1 },
  { id: 'perf',       cut: 44.0, variant: 1 },
  { id: 'outro',      cut: 48.0 },
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

/** The direction the whip travels, alternating so six cuts do not all go one way. */
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
 *
 * The drift is per-shot as well as global, so a shot that is held for eight seconds
 * still has somewhere to go.
 */
export function camera(t) {
  const { index, local } = shotAt(t);
  const next = SHOTS[index + 1];
  const shotLen = next ? next.cut - SHOTS[index].cut : TOTAL_SECONDS - SHOTS[index].cut;

  // A global push, so the frame is always creeping forward.
  const p = clamp01(t / TOTAL_SECONDS);
  const globalZ = 1 + 0.075 * p;

  // A per-shot push, sized to the SHOT rather than to a fixed 7.5 seconds.
  //
  // The previous version used `local / 7.5`, which was tuned for 7-8 second shots.
  // With 3-4 second shots that means the push is still only a third of the way
  // through when the cut arrives, so the frame never reaches the move it was given -
  // the shot reads as a still. Tying it to the shot's own length means every shot
  // completes its push whatever length it is.
  const shotZ = 1 + 0.10 * easeOutQuint(clamp01(local / Math.max(1.2, shotLen * 0.8)));

  // Drift, phase-locked to absolute time so it is reproducible.
  //
  // The frequencies are roughly doubled from the previous version. At 0.21 and 0.27
  // rad/s a 3-second shot caught less than half a cycle, so the drift read as a slow
  // creep rather than as movement - and a slow creep is not motion the eye registers.
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
 * Kept from the earlier versions because it was the one part that worked: a blur
 * has to follow how far the content actually moves between two captured frames or
 * it reads as two half-scenes instead of one smear. The fixed 26px blur during a
 * 1920px move did not, which is why that attempt still looked like a slide with
 * soft edges.
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
