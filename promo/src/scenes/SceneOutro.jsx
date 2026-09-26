// SceneOutro — the call to action, over a wallpaper that is playing.
//
// The logo returns, the button carries a light sweep, and a cursor moves onto it
// and clicks — the same "see it happen" approach used in the other beats. The
// wallpaper behind keeps moving so the closing frame is alive, not a title card.

import React from 'react';
import Aurora from '../Aurora.jsx';
import Logo from '../Logo.jsx';
import SplitText from '../SplitText.jsx';
import WallpaperStage from '../WallpaperStage.jsx';
import { seg, easeOut, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

export default function SceneOutro({ t, global, rt}) {
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
  // this scene were authored for a 7.6s shot; it is now 4.2s, so the whole
  // internal timeline runs 0.55x faster. Without this the animation either
  // never finishes inside the shot or never starts.
  t = t * 0.5526;

  const bg = parallax(global, TOTAL, 0.4, 44);

  const hover = easeOut(seg(t, 1.6, 2.1));
  const clicked = t > 2.5;
  const done = seg(t, 2.7, 3.3);
  const sweep = (t / 2.6) % 1;

  const cx = 960 + (1 - hover) * 300;
  const cy = 690 + (1 - hover) * 120;

  return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translate3d(${idle.x.toFixed(2)}px, ${idle.y.toFixed(2)}px, 0) scale(${idle.s.toFixed(4)})`,
          willChange: 'transform',
        }}
      >
      <div
        style={{
          position: 'absolute',
          inset: '-6%',
          transform: `translate3d(${bg.x}px, ${bg.y}px, 0) scale(${1.12 * bg.scale})`,
        }}
      >
        <WallpaperStage clip="albedo" t={global} offset={6} mode="fill" width="100%" radius={0} />
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(85% 70% at 50% 45%, rgba(7,7,10,.68) 0%, rgba(7,7,10,.92) 60%, rgba(7,7,10,.97) 100%)',
        }}
      />
      <Aurora t={t} intensity={0.26} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 24,
        }}
      >
        <Logo t={t} size={140} delay={0.1} spin />

        {/* The wordmark. The icon alone does not say what the product is called, so
            the outro - which is also the video's poster frame - carries the name.
            Without it the poster is a mark nobody can search for. */}
        <div
          style={{
            fontFamily: FONT,
            fontSize: 40,
            fontWeight: 800,
            letterSpacing: '-.03em',
            color: '#fff',
            marginTop: -6,
            opacity: seg(t, 0.25, 0.85),
            transform: `translateY(${(1 - easeOut(seg(t, 0.25, 0.85))) * 14}px)`,
          }}
        >
          LumaWall
        </div>

        <div style={{ textAlign: 'center', marginTop: -6 }}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 78,
              fontWeight: 800,
              letterSpacing: '-.035em',
              lineHeight: 1,
              color: '#fff',
            }}
          >
            <SplitText text="Gratis. Tanpa iklan." t={t} delay={0.45} stagger={0.032} y={46} />
          </div>
          <div
            style={{
              marginTop: 18,
              fontFamily: FONT,
              // 22px at #a8aeb8 measured 1.49:1 against the wallpaper behind it -
              // the check in tools/check-promo-text.py flagged this line. Grey on a
              // busy image is the worst case: the eye has no edge to follow. White
              // with a shadow, and a little larger.
              fontSize: 26,
              fontWeight: 500,
              color: '#f2f5f8',
              textShadow: '0 2px 12px rgba(0,0,0,.85), 0 0 30px rgba(0,0,0,.6)',
              opacity: seg(t, 1.15, 1.85),
              transform: `translateY(${(1 - easeOut(seg(t, 1.15, 1.85))) * 16}px)`,
            }}
          >
            Windows 10 / 11 · 5.000+ wallpaper · pause per monitor
          </div>
        </div>

        <div style={{ position: 'relative', marginTop: 12 }}>
          <div
            style={{
              position: 'relative',
              overflow: 'hidden',
              // The button is the whole point of the closing shot, and at 19px of
              // padding with 25px type it was a small control in the middle of a
              // large frame. A review of the render called it "small and static" -
              // the size part was right. It is now the largest interactive element
              // in the piece, with a slow pulse so it reads as live rather than as a
              // picture of a button.
              padding: '26px 74px',
              borderRadius: 16,
              background: clicked
                ? 'linear-gradient(180deg,#35e07a,#22a85c)'
                : 'linear-gradient(180deg,#ff4a63,#d92b45)',
              boxShadow: clicked
                ? '0 20px 56px -12px rgba(53,224,122,.7)'
                : '0 20px 56px -12px rgba(255,59,87,.68)',
              opacity: easeOut(seg(t, 1.4, 2.1)),
              transform: `translateY(${(1 - easeOut(seg(t, 1.4, 2.1))) * 26}px)
                          scale(${(1 + hover * 0.025) * (1 + 0.012 * Math.sin(t * 3.1))})`,
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: `${-30 + sweep * 130}%`,
                width: '28%',
                pointerEvents: 'none',
                background:
                  'linear-gradient(100deg, transparent, rgba(255,255,255,.4), transparent)',
              }}
            />
            <span
              style={{
                position: 'relative',
                fontFamily: FONT,
                fontSize: 31,
                fontWeight: 700,
                color: '#fff',
                letterSpacing: '-.01em',
              }}
            >
              {clicked ? 'Unduhan dimulai' : 'Unduh sekarang'}
            </span>
          </div>

          <div
            style={{
              position: 'absolute',
              left: cx - 960 + 220,
              top: cy - 690 + 22,
              width: 26,
              height: 26,
              pointerEvents: 'none',
              filter: 'drop-shadow(0 3px 8px rgba(0,0,0,.75))',
              opacity: t > 1.3 && !clicked ? 1 : 0,
            }}
          >
            <svg viewBox="0 0 24 24" width="26" height="26">
              <path d="M5 2l14 9-6 1.4L16 20l-3 1-3-7-5 4z" fill="#fff" stroke="#111" strokeWidth="1.1" />
            </svg>
          </div>
        </div>

        <div
          style={{
            fontFamily: FONT,
            // The URL is the one thing a viewer has to be able to read if they want
            // the product. At 15px it was a footnote under a button - legible in a
            // frame grab and not on a phone. 22px with wider tracking makes it a
            // line of the composition rather than a caption on it.
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: '.16em',
            color: '#35e07a',
            opacity: done,
            textTransform: 'uppercase',
          }}
        >
          lumawall.xinet.id
        </div>
      </div>
    </div>
  );
}
