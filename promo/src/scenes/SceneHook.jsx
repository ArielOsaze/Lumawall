// SceneHook — the opening: the product, moving, before anything is claimed.
//
// ── the rule this scene follows ──────────────────────────────────────────────
//
// Every scene in the previous promo was a wallpaper with text over it, and the note
// that came back was "semua scene pake wallpaper jelek bgt". This one is the ONE
// place a wallpaper fills the frame, and it earns it: the product IS the wallpaper,
// so the first thing a viewer should see is one playing.
//
// It is also the only scene with no claim in it. A commercial's opening second is
// spent showing, not telling - the argument starts after the viewer has decided to
// keep watching.

import React from 'react';
import { t as tx } from '../copy.js';
import { WallpaperFull, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

export default function SceneHook({ t, global, variant = 0 }) {
  // The wallpaper behind, playing.
  const clip = variant ? 'albedo' : 'raiden';

  // The mark rises and settles, then the wordmark wipes in from behind it.
  const mark = easeOutQuint(seg(t, 0.25, 1.3));
  const word = easeOutQuint(seg(t, 0.85, 1.9));
  const sub = easeOut(seg(t, 1.5, 2.4));
  const rule = easeOut(seg(t, 1.7, 2.6));

  // A slow push on the whole composition, so the frame is never still even while
  // the wallpaper behind it is the thing moving.
  const push = 1 + 0.045 * easeOutQuint(seg(t, 0, 4.2));

  // The scrim is heavier at the start and eases off as the type settles, so the
  // wallpaper is most visible once there is nothing left to read.
  const scrim = 0.78 - 0.20 * easeOut(seg(t, 1.2, 4.0));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, transform: `scale(${push.toFixed(4)})` }}>
        <WallpaperFull clip={clip} t={global} offset={variant ? 5 : 0} scrim={scrim} />
      </div>

      {/* A left-to-right darkening, so the type has a side to live on. This is a
          scrim on the FRAME, not a gradient baked into the video. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(100deg, rgba(6,7,10,.92) 0%, rgba(6,7,10,.74) 34%, rgba(6,7,10,.30) 62%, rgba(6,7,10,.12) 100%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 132px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 26 }}>
          <img
            src="./logo/app-logo.png"
            alt=""
            width={92}
            height={92}
            style={{
              display: 'block',
              width: 92,
              height: 92,
              opacity: mark,
              transform: `scale(${0.82 + 0.18 * mark})`,
              filter: 'drop-shadow(0 10px 30px rgba(0,0,0,.7))',
            }}
          />
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 86,
                fontWeight: 800,
                letterSpacing: '-.04em',
                color: '#fff',
                lineHeight: 1,
                transform: `translateX(${(1 - word) * -100}%)`,
              }}
            >{tx('LumaWall')}</div>
          </div>
        </div>

        <div
          style={{
            marginTop: 30,
            height: 3,
            width: 148,
            background: 'linear-gradient(90deg,#ff3b57,#ff8a5c)',
            transform: `scaleX(${rule})`,
            transformOrigin: 'left center',
          }}
        />

        <div
          style={{
            marginTop: 30,
            fontFamily: FONT,
            fontSize: 34,
            fontWeight: 500,
            lineHeight: 1.4,
            color: '#e6e9ee',
            maxWidth: 760,
            opacity: sub,
            transform: `translateY(${(1 - sub) * 20}px)`,
          }}
        >{tx('Wallpaper hidup di desktop Windows — diproses chip grafis, bukan CPU.')}</div>
      </div>

      {/* The lower third: three short facts, so the opening states the product
          rather than only its name. */}
      <div
        style={{
          position: 'absolute',
          left: 132,
          right: 132,
          bottom: 96,
          display: 'flex',
          gap: 18,
          opacity: easeOut(seg(t, 2.1, 3.1)),
        }}
      >
        {[tx('Windows 10 / 11'), tx('5.000+ wallpaper'), tx('Pause per monitor')].map((s, i) => {
          const k = easeOut(seg(t, 2.1 + i * 0.12, 2.8 + i * 0.12));
          return (
            <span
              key={s}
              style={{
                fontFamily: FONT,
                fontSize: 18,
                fontWeight: 600,
                color: '#d5dae1',
                border: '1px solid rgba(255,255,255,.16)',
                background: 'rgba(255,255,255,.05)',
                borderRadius: 999,
                padding: '10px 20px',
                opacity: k,
                transform: `translateY(${(1 - k) * 16}px)`,
              }}
            >
              {s}
            </span>
          );
        })}
      </div>
    </div>
  );
}
