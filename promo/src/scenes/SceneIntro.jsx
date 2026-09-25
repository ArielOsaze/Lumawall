// SceneIntro — the logo, over a wallpaper that is actually playing.
//
// The old version put the logo on a flat gradient. Here a real wallpaper runs
// behind it, drifting on its own depth plane, so the first frame already shows
// what the product does.

import React from 'react';
import Aurora from '../Aurora.jsx';
import Logo from '../Logo.jsx';
import SplitText from '../SplitText.jsx';
import WallpaperStage from '../WallpaperStage.jsx';
import { seg, easeOut, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

export default function SceneIntro({ t, global }) {
  // The wallpaper drifts on a deeper plane than the type, so it moves less.
  const bg = parallax(global, TOTAL, 0.35, 46);

  const taglineIn = easeOut(seg(t, 1.15, 1.9));
  const subIn = easeOut(seg(t, 1.75, 2.55));

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* A real wallpaper, playing. This is the product, not a mockup.
          Driven by the render clock through WallpaperStage, not a <video>:
          a video element plays from the wall clock, so its content would be
          random per frame and the wallpaper would not appear to move. */}
      <div
        style={{
          position: 'absolute',
          inset: '-6%',
          transform: `translate3d(${bg.x}px, ${bg.y}px, 0) scale(${1.14 * bg.scale})`,
        }}
      >
        <WallpaperStage clip="raiden" t={global} offset={0} mode="fill" width="100%" radius={0} />
      </div>

      {/* Darken it enough for the type to sit on top, but not so much that the
          wallpaper disappears: the whole point of the opening is to show a
          moving wallpaper, and an earlier version darkened it to near-black so
          the frame read as a plain title card. The gradient is strongest behind
          the text and clears towards the edges so the artwork stays visible. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(62% 48% at 50% 46%, rgba(7,7,10,.78) 0%, rgba(7,7,10,.52) 52%, rgba(7,7,10,.30) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(7,7,10,.55) 0%, rgba(7,7,10,.18) 35%, rgba(7,7,10,.22) 70%, rgba(7,7,10,.62) 100%)',
        }}
      />
      <Aurora t={t} intensity={0.14} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 28,
        }}
      >
        <Logo t={t} size={186} delay={0.1} spin minOpacity={0.62} />

        <div style={{ textAlign: 'center', marginTop: 4 }}>
          <div
            style={{
              fontFamily: '"Plus Jakarta Sans", sans-serif',
              fontSize: 96,
              fontWeight: 800,
              letterSpacing: '-.035em',
              lineHeight: 1,
              color: '#fff',
            }}
          >
            <SplitText text="LumaWall" t={t} delay={0.35} stagger={0.05} y={44} opacityFloor={0.5} />
          </div>

          <div
            style={{
              marginTop: 18,
              fontFamily: '"Plus Jakarta Sans", sans-serif',
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: '.32em',
              textTransform: 'uppercase',
              color: '#ff3b57',
              opacity: 0.35 + 0.65 * taglineIn,
              transform: `translateY(${(1 - taglineIn) * 10}px)`,
            }}
          >
            Wallpaper hidup untuk Windows
          </div>
        </div>

        <div
          style={{
            marginTop: 10,
            fontFamily: '"Plus Jakarta Sans", sans-serif',
            fontSize: 24,
            fontWeight: 400,
            color: '#c3c8d0',
            textAlign: 'center',
            maxWidth: 760,
            opacity: 0.3 + 0.7 * subIn,
            transform: `translateY(${(1 - subIn) * 18}px)`,
          }}
        >
          Video berjalan di desktop, didecode GPU, dan berhenti sendiri saat kamu main game.
        </div>
      </div>
    </div>
  );
}
