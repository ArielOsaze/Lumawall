// Timeline — the master clock and the scene transitions.
//
// The old renderer cross-faded between scene functions, which is what made the
// video feel like a PowerPoint deck: for nearly a second two scenes were both
// partly visible, overlapping each other, and nothing moved.
//
// The transition here is a "settle":
//
//   outgoing: fades out quickly (0.38 s) while scaling up slightly, so it reads
//             as receding away from the viewer
//   incoming: fades in while scaling up from 0.97 and rising 44 px, so it reads
//             as arriving and locking into place
//
// A horizontal push was tried first and rejected: both scenes are full-bleed, so
// sliding one left while the other slid right produced visible ghosting of the two
// backgrounds through each other. A scale-settle has no such overlap because the
// fade completes before the scale difference is large.
//
// On top of that, every scene drifts very slowly for its whole life, so no frame
// in the video is ever completely static. Static holds are what make a promo feel
// dead.
//
// The renderer sets the clock explicitly (`window.__setFrame`), so a given frame
// number always produces exactly the same image.

import React, { useState, useEffect } from 'react';
import { seg, easeOut, easeInOut } from './anim.js';
import SceneBoundary from './SceneBoundary.jsx';

import SceneIntro from './scenes/SceneIntro.jsx';
import SceneProblem from './scenes/SceneProblem.jsx';
import SceneCatalog from './scenes/SceneCatalog.jsx';
import SceneMonitors from './scenes/SceneMonitors.jsx';
import ScenePause from './scenes/ScenePause.jsx';
import ScenePerf from './scenes/ScenePerf.jsx';
import SceneOutro from './scenes/SceneOutro.jsx';

// `start` is when a scene begins arriving; `end` is when it has finished leaving.
// Consecutive scenes overlap by TRANSITION seconds.
export const SCENES = [
  { id: 'intro',    start: 0.0,  end: 6.3,  C: SceneIntro },
  { id: 'problem',  start: 5.6,  end: 13.7, C: SceneProblem },
  { id: 'catalog',  start: 13.0, end: 21.4, C: SceneCatalog },
  { id: 'monitors', start: 20.7, end: 29.4, C: SceneMonitors },
  { id: 'pause',    start: 28.7, end: 37.8, C: ScenePause },
  { id: 'perf',     start: 37.1, end: 45.1, C: ScenePerf },
  { id: 'outro',    start: 44.4, end: 52.0, C: SceneOutro },
];

export const TOTAL_SECONDS = 52.0;
export const FPS = 30;

const IN_DUR = 0.55;    // how long the incoming scene takes to settle
const OUT_DUR = 0.38;   // how long the outgoing scene takes to clear

export default function Timeline() {
  const [frame, setFrame] = useState(0);
  const time = frame / FPS;

  useEffect(() => {
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
      }}
    >
      {SCENES.map(({ id, start, end, C }, index) => {
        const span = end - start;
        const local = time - start;
        if (local < -0.001 || local > span + 0.001) return null;

        // Arrival. The first scene does not rise from a previous scene, so it
        // starts already partly visible instead of fading up from nothing: a
        // completely black first frame reads as a broken render and wastes the
        // opening moment.
        const isFirst = index === 0;
        const inK = easeOut(seg(time, start, start + (isFirst ? 0.9 : IN_DUR)));
        const arrive = isFirst ? 0.55 + 0.45 * inK : inK;
        // Departure. The last scene holds to the end - no fade out, so the video
        // ends on the call to action instead of fading to black.
        const isLast = index === SCENES.length - 1;
        const outK = isLast ? 0 : easeInOut(seg(time, end - OUT_DUR, end));

        // The incoming scene MUST fade in. Each scene paints an opaque backdrop,
        // so mounting it at full opacity hides the outgoing scene instantly: the
        // old content disappeared and the new content had not arrived yet, leaving
        // a near-black frame in the middle of every transition.
        const opacity = arrive * (1 - outK);
        const scale = (isFirst ? 1.05 - 0.05 * inK : 0.97 + 0.03 * inK) + 0.018 * (local / span);
        const rise = (1 - inK) * (isFirst ? 0 : 44);

        return (
          <div
            key={id}
            style={{
              position: 'absolute',
              inset: 0,
              opacity,
              transform: `translateY(${rise}px) scale(${scale})`,
              willChange: 'transform, opacity',
            }}
          >
            <SceneBoundary id={id}>
              <C t={local} dur={span} />
            </SceneBoundary>
          </div>
        );
      })}
    </div>
  );
}
