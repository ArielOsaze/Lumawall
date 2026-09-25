// SceneIntro — the logo reveal.
//
// Everything is computed from `t` (seconds since the scene started), so frame N
// is always the same image.

import React from 'react';
import Aurora from '../Aurora.jsx';
import Logo from '../Logo.jsx';
import SplitText from '../SplitText.jsx';
import { seg, easeOut } from '../anim.js';

export default function SceneIntro({ t, dur }) {
  const exit = seg(t, dur - 0.7, dur);
  const ex = easeOut(exit);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} intensity={0.34} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 30,
        }}
      >
        <Logo t={t} size={208} delay={0.12} spin minOpacity={0.62} />

        <div style={{ textAlign: 'center', marginTop: 8 }}>
          <div
            style={{
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 92,
              fontWeight: 700,
              letterSpacing: '-.028em',
              lineHeight: 1,
            }}
          >
            <SplitText
              text="LumaWall"
              t={t}
              delay={0.35}
              stagger={0.048}
              y={44}
              opacityFloor={0.5}
              gradient="linear-gradient(180deg, #ffffff 0%, #cfd2d8 62%, #9aa0aa 100%)"
            />
          </div>

          <div
            style={{
              marginTop: 20,
              fontFamily: '"Cascadia Mono", Consolas, monospace',
              fontSize: 17,
              textTransform: 'uppercase',
              color: '#e2454a',
              opacity: 0.35 + 0.65 * seg(t, 1.15, 1.9),
              letterSpacing: `${0.9 - 0.48 * easeOut(seg(t, 1.45, 2.45))}em`,
            }}
          >
            Live Wallpaper Engine
          </div>
        </div>

        <div
          style={{
            marginTop: 14,
            fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
            fontSize: 25,
            color: '#c8ccd4',
            textAlign: 'center',
            maxWidth: 820,
            opacity: 0.3 + 0.7 * seg(t, 1.75, 2.55),
            transform: `translateY(${(1 - easeOut(seg(t, 1.75, 2.55))) * 22}px)`,
          }}
        >
          Wallpaper video, didecode di GPU — bukan di CPU.
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
          {['Windows 10 / 11', 'Gratis', 'Tanpa iklan'].map((s, i) => {
            const k = 0.4 + 0.6 * seg(t, 2.2 + i * 0.1, 2.7 + i * 0.1);
            const e = easeOut(k);
            return (
              <span
                key={s}
                style={{
                  fontFamily: '"Cascadia Mono", Consolas, monospace',
                  fontSize: 13,
                  letterSpacing: '.06em',
                  color: '#9aa0aa',
                  border: '1px solid rgba(255,255,255,.10)',
                  background: 'rgba(255,255,255,.028)',
                  borderRadius: 999,
                  padding: '7px 15px',
                  opacity: e,
                  transform: `scale(${0.9 + 0.1 * e})`,
                }}
              >
                {s}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
