// SceneClose — the end card.
//
// ── why the close is not another wallpaper ──────────────────────────────────
//
// The previous version ended on a wallpaper with the logo over it, which is the same
// frame as the opening - so the piece finished where it started and the last thing a
// viewer saw was a repeat.
//
// A close has one job: leave the name and the way to get it. So it is a quiet brand
// frame, the mark and the wordmark in the middle, one line, and the availability. The
// wallpaper appears once, small, as a preview inside the product frame - because by
// this point the viewer knows what the product does and only needs to be told what it
// is called and where to get it.

import React from 'react';
import { Surface, Type, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, easeOutExpo } from '../anim.js';

export default function SceneClose({ t, global, variant = 0 }) {
  const mark = easeOutQuint(seg(t, 0.15, 1.0));
  const word = easeOutQuint(seg(t, 0.45, 1.3));
  const line = easeOut(seg(t, 0.85, 1.6));
  const pill = easeOutExpo(seg(t, 1.15, 1.9));
  const preview = easeOutQuint(seg(t, 1.0, 2.0));

  // A slow push that never stops, so the last shot is alive to the final frame.
  const push = 1 + 0.03 * seg(t, 0, 5);

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.15} warmSide="right" />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 96,
          padding: '0 120px',
          transform: `scale(${push.toFixed(4)})`,
        }}
      >
        {/* ── the mark and the way to get it ────────────────────────────────── */}
        <div style={{ maxWidth: 660 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <img
              src="./logo/app-logo.png"
              alt=""
              style={{
                display: 'block',
                width: 84,
                height: 84,
                opacity: mark,
                transform: `scale(${0.84 + 0.16 * mark})`,
                filter: 'drop-shadow(0 10px 30px rgba(0,0,0,.7))',
              }}
            />
            <div
              style={{
                fontFamily: FONT,
                fontSize: 76,
                fontWeight: 800,
                letterSpacing: '-.04em',
                color: '#fff',
                lineHeight: 1,
                opacity: word,
                transform: `translateX(${(1 - word) * -26}px)`,
              }}
            >
              LumaWall
            </div>
          </div>

          <div
            style={{
              marginTop: 28,
              fontFamily: FONT,
              fontSize: 30,
              fontWeight: 500,
              lineHeight: 1.45,
              color: '#d5dae1',
              opacity: line,
              transform: `translateY(${(1 - line) * 18}px)`,
            }}
          >
            Wallpaper hidup, tanpa membebani komputer.
          </div>

          {/* The call to action, as a pill rather than as a sentence. */}
          <div
            style={{
              marginTop: 40,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 14,
              padding: '17px 30px',
              borderRadius: 999,
              background: 'linear-gradient(120deg,#ff3b57,#ff6b3d)',
              opacity: pill,
              transform: `translateY(${(1 - pill) * 18}px)`,
              boxShadow: '0 22px 50px -20px rgba(255,59,87,.65)',
            }}
          >
            <span style={{ fontFamily: FONT, fontSize: 22, fontWeight: 700, color: '#fff' }}>
              Unduh gratis di lumawall.xinet.id
            </span>
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <div
            style={{
              marginTop: 26,
              display: 'flex',
              gap: 14,
              opacity: pill,
            }}
          >
            {['Windows 10 / 11', 'Gratis', 'Tanpa akun'].map((s) => (
              <span
                key={s}
                style={{
                  fontFamily: FONT,
                  fontSize: 17,
                  fontWeight: 600,
                  color: '#c3c8d0',
                  border: '1px solid rgba(255,255,255,.14)',
                  borderRadius: 999,
                  padding: '9px 18px',
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* ── the product, once, small ──────────────────────────────────────── */}
        <div
          style={{
            opacity: preview,
            transform: `translateY(${(1 - preview) * 30}px) scale(${0.95 + 0.05 * preview})`,
          }}
        >
          <div
            style={{
              borderRadius: 14,
              padding: 9,
              background: 'linear-gradient(180deg,#26282f,#15161a)',
              boxShadow: '0 50px 110px -40px rgba(0,0,0,.95)',
            }}
          >
            <Wallpaper clip={variant ? 'raiden' : 'albedo'} t={global} width={540} radius={8} />
          </div>
        </div>
      </div>
    </div>
  );
}
