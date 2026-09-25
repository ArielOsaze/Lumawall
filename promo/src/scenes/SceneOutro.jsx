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

export default function SceneOutro({ t, global }) {
  const bg = parallax(global, TOTAL, 0.4, 44);

  const hover = easeOut(seg(t, 1.6, 2.1));
  const clicked = t > 2.5;
  const done = seg(t, 2.7, 3.3);
  const sweep = (t / 2.6) % 1;

  const cx = 960 + (1 - hover) * 300;
  const cy = 690 + (1 - hover) * 120;

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
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
              fontSize: 22,
              color: '#a8aeb8',
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
              padding: '19px 52px',
              borderRadius: 13,
              background: clicked
                ? 'linear-gradient(180deg,#35e07a,#22a85c)'
                : 'linear-gradient(180deg,#ff4a63,#d92b45)',
              boxShadow: clicked
                ? '0 16px 44px -12px rgba(53,224,122,.65)'
                : '0 16px 44px -12px rgba(255,59,87,.6)',
              opacity: easeOut(seg(t, 1.4, 2.1)),
              transform: `translateY(${(1 - easeOut(seg(t, 1.4, 2.1))) * 26}px)
                          scale(${1 + hover * 0.025})`,
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
                fontSize: 25,
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
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: '.14em',
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
