// Timeline — one continuous camera move for the whole video.
//
// What was wrong before: the promo cut between scenes. Each one faded in, held
// still, then faded out. That is a slideshow, and no amount of polish on the
// individual frames changes what it is.
//
// What it does now: there is a single camera for all 52 seconds and it never
// stops moving — a slow push in, a sideways drift, a fraction of a degree of
// roll. The beats are placed along the camera's path and the camera travels past
// them. A transition is the camera arriving somewhere new, not one picture
// replacing another, so no frame is ever static and two beats are never both
// half-visible.
//
// Every scene also receives the global time, so it can place its own content in
// the camera's world rather than inside its own little box.

import React, { useState, useEffect } from 'react';
import { cameraTransform, seg, easeInOut, easeOut, clamp01 } from './anim.js';
import SceneBoundary from './SceneBoundary.jsx';

import SceneIntro from './scenes/SceneIntro.jsx';
import SceneProblem from './scenes/SceneProblem.jsx';
import SceneCatalog from './scenes/SceneCatalog.jsx';
import SceneMonitors from './scenes/SceneMonitors.jsx';
import ScenePause from './scenes/ScenePause.jsx';
import ScenePerf from './scenes/ScenePerf.jsx';
import SceneOutro from './scenes/SceneOutro.jsx';

export const TOTAL_SECONDS = 52.0;
export const FPS = 30;

// Each beat occupies a window. Consecutive windows overlap, and the camera
// travels through the overlap, so the handover is a movement rather than a cut.
export const BEATS = [
  { id: 'intro',    from: 0.0,  to: 7.4,  C: SceneIntro },
  { id: 'problem',  from: 6.4,  to: 14.6, C: SceneProblem },
  { id: 'catalog',  from: 13.6, to: 22.4, C: SceneCatalog },
  { id: 'monitors', from: 21.4, to: 30.4, C: SceneMonitors },
  { id: 'pause',    from: 29.4, to: 38.6, C: ScenePause },
  { id: 'perf',     from: 37.6, to: 45.6, C: ScenePerf },
  { id: 'outro',    from: 44.6, to: 52.0, C: SceneOutro },
];

// How long the camera takes to travel from one beat to the next.
const TRAVEL = 1.6;

// How far a beat slides during the handover, in pixels. This is the full frame
// width, because the handover is a pan rather than a dissolve: the outgoing beat
// has to leave the frame completely before the incoming one has fully arrived.
const SLIDE = 1920;

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
        background: '#07070a',
        // One camera for the whole piece.
        transform: cameraTransform(time, TOTAL_SECONDS),
        transformOrigin: '50% 48%',
        willChange: 'transform',
      }}
    >
      {BEATS.map(({ id, from, to, C }, i) => {
        const next = BEATS[i + 1];

        // ── the handover curve ───────────────────────────────────────────────
        //
        // Two beats are on screen at once during a handover, so their opacities
        // have to sum to about 1 at every instant. The previous version used
        // `arrive` for the incoming beat and `leave` for the outgoing one
        // independently, and because both eased differently the two stayed fully
        // visible at the same time for roughly half a second. On screen that is
        // two headings and two sets of figures overlapping, which a review read
        // as a glitch.
        //
        // One shared progress value drives both, so the outgoing beat is always
        // exactly as faded out as the incoming one is faded in.
        // Arrival and departure are both full-width movements. There is no
        // opacity crossfade at all: the beats stay solid and the camera carries
        // them past each other.
        const kIn = i === 0 ? 1 : easeInOut(seg(time, from, from + TRAVEL));
        const kOut = next ? easeInOut(seg(time, next.from, next.from + TRAVEL)) : 0;

        // Outside its own window a beat is either not here yet or already gone.
        if (time < from - 0.05) return null;
        if (next && time > next.from + TRAVEL + 0.05) return null;

        // Solid throughout. A beat is only invisible when it is off the frame,
        // which the slide below guarantees.
        const opacity = 1;

        // A directional push, not a zoom.
        //
        // The previous version scaled each incoming beat from 0.965 to 1 while
        // the camera was also scaling the whole frame, so every handover zoomed
        // twice at different rates. On screen that reads as a mistake, and it was
        // the "weird zoom" in the transitions.
        //
        // Now the incoming beat slides in from the right and the outgoing one
        // continues to the left: both move the same way, matching the camera's
        // own left-to-right drift, so the handover reads as the camera panning
        // past a boundary rather than a picture replacing another.
        const enterX = (1 - kIn) * SLIDE;
        const exitX = -kOut * SLIDE;

        // Two planes, not one. The scene's own wallpaper moves at 40% of the
        // slide and its content at 100%, so the handover has depth: the near
        // layer outruns the far one, which is what a camera moving past a
        // boundary actually does. A single flat slide read as one sheet of paper.
        const drift = enterX + exitX;

        return (
          <div
            key={id}
            style={{
              position: 'absolute',
              inset: 0,
              opacity,
              // The far plane: the scene drifts, but less than its content.
              transform: `translate3d(${drift * 0.4}px, 0, 0)`,
              willChange: 'transform, opacity',
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: 0,
                // The near plane: content travels the full distance.
                transform: `translate3d(${drift * 0.6}px, 0, 0)`,
              }}
            >
            <SceneBoundary id={id}>
              <C t={time - from} start={from} end={to} global={time} />
            </SceneBoundary>
            </div>
          </div>
        );
      })}

      {/* ── grade ──────────────────────────────────────────────────────────
          One cinematic pass over the whole piece, rather than effects on each
          scene. Three things, all subtle:

            · a vignette, which darkens the corners and pushes the eye inward
            · a warm rim top-left and a cool one bottom-right, so the frame has
              a light direction instead of being uniformly flat
            · the faintest grain, which stops large dark areas from banding

          A design review of the previous cut called the backgrounds "flat" and
          asked for depth and lighting. This is that, applied once. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(126% 100% at 50% 46%, rgba(0,0,0,0) 52%, rgba(0,0,0,.13) 80%, rgba(0,0,0,.28) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(58% 44% at 12% 6%, rgba(255,222,205,.028) 0%, rgba(255,222,205,0) 70%), ' +
            'radial-gradient(62% 48% at 92% 96%, rgba(170,215,255,.026) 0%, rgba(170,215,255,0) 72%)',
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
