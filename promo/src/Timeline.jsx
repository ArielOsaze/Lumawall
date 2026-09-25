// Timeline — the camera, the beats, and the handovers between them.
//
// ── the handovers, and why the earlier attempts still read as slides ─────────
//
// Three cuts in a row failed the same way and each fix addressed the wrong thing:
//
//   1. Crossfade. Both beats semi-visible in the same place. A review picked out
//      the frame; it read as a glitch even with the opacities summing to exactly 1.
//   2. Full-width pan. No overlap, but it moved 1920px over 1.6 seconds with no
//      blur, which is precisely PowerPoint's "Push" transition.
//   3. Pan with blur. Closer, but the blur was a fixed 26px while the scene moved
//      1920px. The blur was 1/80th of the motion, so the frame showed two distinct
//      half-scenes rather than one smear — a slide with soft edges, still a slide.
//
// The cause is arithmetic: **the blur has to match how far the content moves
// between two captured frames.** At 30fps a 1920px move over 1.6s is 40px per
// frame, and a 26px blur is nearly invisible. A move of 1100px over 0.34s is
// ~108px per frame average and ~200px at the peak of the easing, so the blur has
// to be in that range to read as one continuous smear.
//
// So the blur is now derived from the velocity rather than set by hand, and the
// handover is fast enough that the eye cannot track the movement — which is what
// makes a whip pan read as a camera rather than as a slide.
//
// The zoom-through handovers work the same way: a radial blur is approximated by
// scaling and blurring together, and the amount is tied to how fast the scale is
// changing.

import React, { useState, useEffect } from 'react';
import { cameraTransform, seg, easeInOut, easeOut, clamp01 } from './anim.js';
import SceneBoundary from './SceneBoundary.jsx';
import MotionFilters, { WHIP_BLUR, ZOOM_BLUR } from './MotionFilters.jsx';

import SceneIntro from './scenes/SceneIntro.jsx';
import SceneProblem from './scenes/SceneProblem.jsx';
import SceneCatalog from './scenes/SceneCatalog.jsx';
import SceneMonitors from './scenes/SceneMonitors.jsx';
import ScenePause from './scenes/ScenePause.jsx';
import ScenePerf from './scenes/ScenePerf.jsx';
import SceneOutro from './scenes/SceneOutro.jsx';

export const TOTAL_SECONDS = 52.0;
export const FPS = 30;

export const BEATS = [
  { id: 'intro',    from: 0.0,  to: 7.2,  C: SceneIntro },
  { id: 'problem',  from: 7.2,  to: 14.8, C: SceneProblem },
  { id: 'catalog',  from: 14.8, to: 22.4, C: SceneCatalog },
  { id: 'monitors', from: 22.4, to: 30.6, C: SceneMonitors },
  { id: 'pause',    from: 30.6, to: 38.2, C: ScenePause },
  { id: 'perf',     from: 38.2, to: 45.4, C: ScenePerf },
  { id: 'outro',    from: 45.4, to: 52.0, C: SceneOutro },
];

// How long a handover takes. This is the single most important number here: at
// 0.34s the movement is faster than the eye can track, which is what makes it a
// whip. The 1.6s this started at was slow enough to read every pixel of the slide.
const HANDOVER = 0.26;

// How far the content travels during a handover. Deliberately less than the frame
// width: the blur carries the transition, and a shorter travel means a blur that
// is large enough to read without being a smear you cannot see through.
const TRAVEL_X = 1080;
const TRAVEL_Y = 620;

// Every scene is drawn oversized so that a blurred edge never reaches the frame.
// Without this, `filter: blur()` softens the scene's own border and the background
// shows through it as a soft frame around the picture.
const BLEED = 0.16;

// The blur amount lives in MotionFilters, because it has to be directional: CSS
// blur() is isotropic and produced a muddy frame rather than a smear. See that
// file for the full reasoning.

// How each beat leaves. Varying the direction stops six handovers in a row from
// reading as one mechanical movement.
const HANDOVERS = [
  { kind: 'whip', axis: 'x', dir: 1 },   // intro    -> problem
  { kind: 'zoom' },                      // problem  -> catalog
  { kind: 'whip', axis: 'y', dir: 1 },   // catalog  -> monitors
  { kind: 'whip', axis: 'x', dir: -1 },  // monitors -> pause
  { kind: 'zoom' },                      // pause    -> perf
  { kind: 'whip', axis: 'x', dir: 1 },   // perf     -> outro
];

export default function Timeline() {
  const [frame, setFrame] = useState(0);
  const time = frame / FPS;

  useEffect(() => {
    // The renderer drives time. It must never be driven by the browser, or the
    // output would not be reproducible.
    window.__setFrame = (f) => setFrame(f);
    window.__ready = true;
    return () => {
      delete window.__setFrame;
      delete window.__ready;
    };
  }, []);

  return (
    <div
      style={{
        position: 'relative',
        width: 1920,
        height: 1080,
        overflow: 'hidden',
        background: '#08090d',
      }}
    >
      {/* The whip filters. One <defs> block for the whole piece; the scenes
          reference them by id. */}
      <MotionFilters />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: cameraTransform(time, TOTAL_SECONDS),
          transformOrigin: '50% 48%',
          willChange: 'transform',
        }}
      >
        {BEATS.map(({ id, from, to, C }, i) => {
          const next = BEATS[i + 1];

          // Progress of the handover into this beat, and out of it.
          const kIn = i === 0 ? 1 : easeInOut(seg(time, from, from + HANDOVER));
          const kOut = next ? easeInOut(seg(time, next.from, next.from + HANDOVER)) : 0;

          // Outside its own window a beat is either not here yet or already gone.
          if (time < from - 0.02) return null;
          if (next && time > next.from + HANDOVER + 0.02) return null;

          let tx = 0, ty = 0, scale = 1, opacity = 1;
          // Which filter to apply, and how far through its range. An empty string
          // means no filter at all, which is the case for most of every beat.
          let filterId = '';
          let filterAmount = 0;

          // ── arriving ────────────────────────────────────────────────────────
          if (i > 0 && kIn < 1) {
            const h = HANDOVERS[i - 1];
            if (h.kind === 'whip') {
              const d = 1 - kIn;
              if (h.axis === 'x') {
                tx = h.dir * TRAVEL_X * d;
                filterId = 'whip-x';
              } else {
                ty = h.dir * TRAVEL_Y * d;
                filterId = 'whip-y';
              }
            } else {
              // Zoom-through: arrives small and soft, like a lens finding the
              // subject. The scale carries the motion; the blur only softens it.
              scale *= 0.55 + 0.45 * kIn;
              filterId = 'zoom';
              opacity = Math.min(opacity, 0.15 + 0.85 * kIn);
            }
            filterAmount = Math.sin(kIn * Math.PI);
          }

          // ── leaving ─────────────────────────────────────────────────────────
          if (next && kOut > 0) {
            const h = HANDOVERS[i];
            let outAmount = 0;
            let outFilter = '';
            if (h.kind === 'whip') {
              if (h.axis === 'x') {
                tx -= h.dir * TRAVEL_X * kOut;
                outFilter = 'whip-x';
              } else {
                ty -= h.dir * TRAVEL_Y * kOut;
                outFilter = 'whip-y';
              }
            } else {
              // Flies past the lens.
              scale *= 1 + 1.9 * kOut;
              outFilter = 'zoom';
              opacity = Math.min(opacity, 1 - 0.9 * kOut);
            }
            outAmount = Math.sin(kOut * Math.PI);

            // The stronger of the two, and its filter. A beat can be leaving one
            // way and arriving another, and only one filter can apply.
            if (outAmount > filterAmount) {
              filterAmount = outAmount;
              filterId = outFilter;
            }
          }

          // A little push during a whip, so the movement has some Z to it. Small:
          // this is a rush, not a zoom.
          const rushing = (i > 0 && kIn < 1 && HANDOVERS[i - 1].kind === 'whip') ||
                          (next && kOut > 0 && HANDOVERS[i].kind === 'whip');
          if (rushing) {
            const r = Math.max(
              i > 0 && kIn < 1 ? Math.sin(kIn * Math.PI) : 0,
              next && kOut > 0 ? Math.sin(kOut * Math.PI) : 0,
            );
            scale *= 1 + 0.12 * r;
          }

          // The blur only applies in the middle of a handover, where the content
          // is genuinely moving fast. Fading it in and out at the ends is what
          // stops the scene from looking soft when it is standing still.
          const filter = filterId && filterAmount > 0.12
            ? `url(#${filterId})`
            : 'none';

          return (
            <div
              key={id}
              style={{
                position: 'absolute',
                // Oversized by the bleed, so a blurred edge never reaches the
                // frame and the background never shows through a soft border.
                inset: `-${BLEED * 100}%`,
                opacity,
                transform: `translate3d(${tx.toFixed(1)}px, ${ty.toFixed(1)}px, 0) scale(${scale.toFixed(4)})`,
                filter,
                willChange: 'transform, filter, opacity',
              }}
            >
              {/* The far plane lags the frame slightly, which is what gives a
                  handover depth: the background does not travel as far as the
                  content in front of it. */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  transform: `translate3d(${(-tx * 0.14).toFixed(1)}px, ${(-ty * 0.14).toFixed(1)}px, 0)`,
                }}
              >
                {/* The scene is laid out against the FRAME, not against the
                    bleed box. Percentage insets resolve against the containing
                    block, so the box above is 1920 x 1.32 = 2534 wide, and a
                    scene that pads by 130 px expecting a 1920-wide frame ends
                    up with its first element starting at -177. That is what
                    pushed the Perf scene's CPU card off the left edge, and the
                    same arithmetic clipped every other scene's left margin.

                    This wrapper pulls the layout box back to the frame's own
                    size, centred in the bleed, so scenes can be written against
                    1920 x 1080 and stay there whatever the bleed is. */}
                <div
                  style={{
                    position: 'absolute',
                    // The offset is a share OF THE BOX, not of the frame: the
                    // wrapper has to sit exactly one bleed inside the box, and
                    // the box is (1 + 2*BLEED) times the frame. Using BLEED
                    // directly put it 98 px right of centre.
                    left: `${(BLEED / (1 + 2 * BLEED)) * 100}%`,
                    top: `${(BLEED / (1 + 2 * BLEED)) * 100}%`,
                    width: `${100 / (1 + 2 * BLEED)}%`,
                    height: `${100 / (1 + 2 * BLEED)}%`,
                  }}
                >
                  <SceneBoundary id={id}>
                    <C t={time - from} start={from} end={to} global={time} />
                  </SceneBoundary>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── grade ──────────────────────────────────────────────────────────
          Fixed to the frame rather than to the camera, so the vignette does not
          travel with the scenes.

          Three things, all subtle: a vignette to close the corners, a warm rim
          top-left and a cool one bottom-right so the frame has a light direction,
          and the faintest grain to stop large dark areas from banding. Kept light
          on purpose — a heavier version was reviewed as crushing the wallpaper,
          and in a promo for a wallpaper app the wallpaper is the product. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(126% 100% at 50% 46%, rgba(0,0,0,0) 52%, rgba(0,0,0,.13) 80%, rgba(0,0,0,.30) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(58% 44% at 12% 6%, rgba(255,222,205,.030) 0%, rgba(255,222,205,0) 70%), ' +
            'radial-gradient(62% 48% at 92% 96%, rgba(170,215,255,.028) 0%, rgba(170,215,255,0) 72%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          opacity: 0.028,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}
