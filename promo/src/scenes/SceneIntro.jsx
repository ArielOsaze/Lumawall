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

export default function SceneIntro({ t, global, rt}) {
  // The raw shot clock, before the retime below scales it. The idle motion
  // runs on this, so it is smooth at the same rate in every scene whatever factor
  // that scene was retimed by.
  const rawT = t;
  // ── idle motion ────────────────────────────────────────────────────────
  // This scene's animation finishes after a second or two, and the shot runs
  // for four. A frame that stops moving and then waits to be cut is a slide -
  // which is what the whole piece was being described as. So the scene keeps
  // drifting and breathing for its entire life.
  //
  // Small on purpose: 10px of travel and 0.6% of scale over the shot. The eye
  // should not read it as a move; it should simply never see the same frame
  // twice.
  const idle = {
    x: Math.sin(rawT * 1.7) * 5 + rawT * 2.5,
    y: Math.cos(rawT * 2.1) * 3.5 - rawT * 1.6,
    s: 1 + 0.006 * (1 - Math.cos(rawT * 1.35)) / 2 + rawT * 0.0015,
  };

  // Animation clock, scaled to this shot's new length. The delays in
  // this scene were authored for a 7.2s shot; it is now 3.4s, so the whole
  // internal timeline runs 0.47x faster. Without this the animation either
  // never finishes inside the shot or never starts.
  t = t * 0.4722;

  // The wallpaper drifts on a deeper plane than the type, so it moves less.
  const bg = parallax(global, TOTAL, 0.35, 46);

  const taglineIn = easeOut(seg(t, 1.15, 1.9));
  const subIn = easeOut(seg(t, 1.75, 2.55));

  return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translate3d(${idle.x.toFixed(2)}px, ${idle.y.toFixed(2)}px, 0) scale(${idle.s.toFixed(4)})`,
          willChange: 'transform',
        }}
      >
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
            'radial-gradient(58% 46% at 50% 47%, rgba(7,7,10,.70) 0%, rgba(7,7,10,.40) 54%, rgba(7,7,10,.20) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(7,7,10,.44) 0%, rgba(7,7,10,.12) 34%, rgba(7,7,10,.16) 68%, rgba(7,7,10,.50) 100%)',
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
          Diproses chip grafis. Berhenti sendiri saat kamu main game.
        </div>
      </div>
    </div>
  );
}
