// BrandStage — the clean environment for scenes that are about the app rather
// than about a wallpaper.
//
// Why this exists: every scene used to sit on a wallpaper, so the whole 52
// seconds read as one texture. A review called it monotonous, and it is worse
// than monotonous — it is a missed argument. A scene that is about measured CPU
// usage wants a quiet, branded surface so the figures are the only thing
// competing for attention. Showing a wallpaper behind the numbers says nothing
// and costs the wallpaper its impact when it does appear.
//
// So the wallpaper now appears where it means something: the opening, inside the
// app's own frames, and the close. Everything between sits on this.
//
// What it is: a deep base, two slow-drifting colour blooms in the brand's own
// palette, and a faint grid that drifts. All three are driven by absolute time so
// a re-render is identical, and all three are slow enough to read as atmosphere
// rather than as animation.

import React from 'react';
import { loop, seg, easeOut } from './anim.js';

export default function BrandStage({
  t,
  // How strongly the blooms show. The default is deliberately low: this is a
  // background, and a background that competes with the content is a worse
  // background.
  intensity = 1,
  // A faint engineering grid. Off for scenes where even that is too much.
  grid = true,
  // Which side the warm bloom sits on, so consecutive scenes are not identical.
  warmSide = 'left',
  // Fades the whole stage up at the start of a scene, so it arrives rather than
  // appearing.
  fadeIn = 0,
}) {
  // Two independent periods that share no small common multiple, so the pattern
  // never visibly repeats inside the length of the piece.
  const a = loop(t, 26, 0);
  const b = loop(t, 34, 0.4);

  const ax = Math.cos(a * Math.PI * 2) * 12;
  const ay = Math.sin(a * Math.PI * 2) * 8;
  const bx = Math.cos(b * Math.PI * 2) * 10;
  const by = Math.sin(b * Math.PI * 2) * 9;

  const warmAt = warmSide === 'left' ? '22% 30%' : '78% 34%';
  const coolAt = warmSide === 'left' ? '82% 74%' : '18% 70%';

  const opacity = fadeIn > 0 ? easeOut(seg(t, 0, fadeIn)) : 1;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        opacity,
        // Not pure black. A very dark blue-grey reads as a lit surface; pure
        // black reads as a hole, and banding shows on the gradients.
        background: '#08090d',
      }}
    >
      {/* The brand's own red, drifting. This is the light the scene is lit by. */}
      <div
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(46% 40% at calc(${warmAt.split(' ')[0]} + ${ax}%) calc(${warmAt.split(' ')[1]} + ${ay}%), rgba(255,46,67,${0.16 * intensity}) 0%, rgba(255,46,67,0) 68%)`,
        }}
      />
      {/* A cool counter-light, so the frame has a direction rather than a wash. */}
      <div
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(50% 44% at calc(${coolAt.split(' ')[0]} + ${bx}%) calc(${coolAt.split(' ')[1]} + ${by}%), rgba(64,140,255,${0.10 * intensity}) 0%, rgba(64,140,255,0) 70%)`,
        }}
      />

      {grid && (
        <div
          style={{
            position: 'absolute',
            inset: '-10%',
            opacity: 0.5,
            // A 64px grid, drifting a few pixels. At this contrast it is texture,
            // not a grid: you notice it only if you look for it.
            backgroundImage:
              'linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px), ' +
              'linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px)',
            backgroundSize: '64px 64px',
            transform: `translate3d(${ax * 1.6}px, ${ay * 1.6}px, 0)`,
          }}
        />
      )}

      {/* A vignette closes the corners so the eye stays in the middle. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(120% 96% at 50% 46%, rgba(0,0,0,0) 46%, rgba(0,0,0,.34) 82%, rgba(0,0,0,.62) 100%)',
        }}
      />
    </div>
  );
}
