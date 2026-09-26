// Timeline — hard cuts on motion, one camera, no transition effects.
//
// ── the change, and why ─────────────────────────────────────────────────────
//
// The previous version put seven scenes in one 2D box and animated a handover
// between each pair. Four rounds went into those handovers - crossfade, slide,
// slide with blur, blur from velocity - and the note that came back each time was
// still "like a PowerPoint". Every round assumed the join was the problem.
//
// It was not. A visible transition is a transition effect, and transition effects
// are what presentation software has. Broadcast work cuts, and lands the cut on
// movement so the eye follows the motion rather than noticing the join.
//
// So: no crossfade, no push, no wipe, and nothing travels between shots. Each shot
// cuts in already moving, and the only technique at a boundary is a 0.17s
// directional smear that peaks exactly on the cut frame - a whip-pan cut.
//
// The other half is that no shot is a still. A camera that is always pushing and
// drifting means the frame is never static, and a static frame is what a slide is.

import React, { useState, useEffect } from 'react';
import {
  TOTAL_SECONDS, FPS, FRAME_W, FRAME_H, SHOTS, shotAt, cutWhip, cutAngle,
  cameraTransform, motionBlur, shotProgress,
} from './Direction.jsx';
import MotionFilters from './MotionFilters.jsx';
import SceneBoundary from './SceneBoundary.jsx';

import SceneHook from './scenes/SceneHook.jsx';
import SceneProblem from './scenes/SceneProblem.jsx';
import SceneBrowse from './scenes/SceneBrowse.jsx';
import SceneApply from './scenes/SceneApply.jsx';
import SceneMulti from './scenes/SceneMulti.jsx';
import ScenePause from './scenes/ScenePause.jsx';
import SceneGpu from './scenes/SceneGpu.jsx';
import ScenePerf from './scenes/ScenePerf.jsx';
import SceneQuality from './scenes/SceneQuality.jsx';
import SceneLibrary from './scenes/SceneLibrary.jsx';
import SceneClose from './scenes/SceneClose.jsx';

// One entry per shot, and every id in SHOTS has one. There is no scene here that
// appears twice: the previous revision cut the same seven scenes twice, and a
// review caught the repeat by eye.
const SCENES = {
  hook: SceneHook,
  problem: SceneProblem,
  browse: SceneBrowse,
  apply: SceneApply,
  multi: SceneMulti,
  pause: ScenePause,
  gpu: SceneGpu,
  perf: ScenePerf,
  quality: SceneQuality,
  library: SceneLibrary,
  close: SceneClose,
};

export { TOTAL_SECONDS, FPS };

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

  // `shotAt` returns the shot AND how long it has been running. Reading `local` off
  // SHOTS[index] instead gives `undefined`, because SHOTS entries only carry
  // { id, cut } - and an undefined time makes every number in the scene NaN.
  const shot = shotAt(time);
  const C = SCENES[shot.id];
  const entry = SHOTS[shot.index];

  // A missing scene is a blank shot in the finished video, and nothing would fail -
  // so it is made loud here instead.
  if (!C) {
    throw new Error(`no scene is registered for shot id "${shot.id}" at ${time.toFixed(2)}s`);
  }

  // The whip at a cut. It peaks on the cut frame and clears fast, so the incoming
  // shot is readable almost immediately.
  const whip = cutWhip(time);
  const angle = cutAngle(time);

  // The camera's own motion, which is always running. Kept small: this is the
  // frame breathing, not a move.
  const drift = motionBlur(time);

  // The whip dominates at a cut; between cuts only the camera's own drift applies.
  const blur = Math.max(whip * 34, drift);

  return (
    <div
      style={{
        position: 'relative',
        width: FRAME_W,
        height: FRAME_H,
        overflow: 'hidden',
        background: '#07080b',
      }}
    >
      <MotionFilters blur={blur} angle={angle} />

      {/* The camera. It runs for the whole piece and is never reset, so no shot is
          ever a still image - which is half of why the earlier versions read as a
          deck of static frames. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: cameraTransform(time),
          transformOrigin: '50% 48%',
          willChange: 'transform',
          filter: blur > 0.9 ? 'url(#motion)' : 'none',
        }}
      >
        {/* Only the current shot is mounted. A cut means one shot replaces another
            on a single frame - there is no moment where two are both visible, which
            is exactly what a crossfade is and exactly what this removes. */}
        <SceneBoundary id={shot.id}>
          <C
            t={shot.local}
            global={time}
            start={shot.cut}
            end={TOTAL_SECONDS}
            variant={entry.variant || 0}
          />
        </SceneBoundary>
      </div>

      {/* ── grade ─────────────────────────────────────────────────────────────
          Fixed to the frame, so the vignette and the grain do not travel with the
          camera. Three things, all subtle: a vignette to close the corners, a warm
          rim top-left and a cool one bottom-right so the frame has a light
          direction, and the faintest grain to stop large dark areas banding. Kept
          light on purpose - in a promo for a wallpaper app the wallpaper is the
          product, and a heavier grade was reviewed as crushing it. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(128% 102% at 50% 46%, rgba(0,0,0,0) 54%, rgba(0,0,0,.12) 82%, rgba(0,0,0,.28) 100%)',
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
