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

        // Arrive: the beat is fully present TRAVEL seconds after it starts.
        const arrive = easeOut(seg(time, from, from + TRAVEL));
        // Leave: it starts moving away TRAVEL seconds before the next beat is
        // fully present, so the two overlap and the camera carries the change.
        const leave = next ? easeInOut(seg(time, next.from, next.from + TRAVEL)) : 0;

        // Before its window the beat has not been reached; once the next one is
        // established it is behind the camera.
        if (time < from - 0.05) return null;
        if (next && time > next.from + TRAVEL + 0.05) return null;

        // Opacity only dips far enough to hide the handover, never to black.
        const opacity = clamp01(arrive * (1 - leave));

        // The incoming beat rises and settles; the outgoing one drifts back.
        const rise = (1 - arrive) * 60;
        const sink = leave * -46;
        const scale = 0.965 + 0.035 * arrive;

        return (
          <div
            key={id}
            style={{
              position: 'absolute',
              inset: 0,
              opacity,
              transform: `translate3d(0, ${rise + sink}px, 0) scale(${scale})`,
              willChange: 'transform, opacity',
            }}
          >
            <SceneBoundary id={id}>
              <C t={time - from} start={from} end={to} global={time} />
            </SceneBoundary>
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
