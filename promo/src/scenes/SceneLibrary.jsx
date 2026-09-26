// SceneLibrary — the library, as a wall of the actual product.
//
// ── what this scene is for, and why it is not the catalogue scene again ─────
//
// The catalogue scene shows the app being searched: one screen, one cursor, one
// interaction. This one is about SCALE - that the library is large and that the things
// in it are the wallpapers you actually want.
//
// The device for that is a wall of live previews, each playing a real clip, drifting
// slowly across the frame like a wall of screens. It is the one place in the piece
// where more than one wallpaper is on screen at once, and it is the scene that answers
// "what do I get".
//
// Every tile is at the clip's own aspect ratio. Nothing is cropped.

import React from 'react';
import { Surface, Type, Eyebrow, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

// Three rows, four clips, so the wall reads as a library rather than as a list.
const ROWS = [
  { y: -12, x: -6, items: ['raiden', 'astra', 'albedo', 'i14'], speed: 1.0, scale: 0.92 },
  { y: 34, x: -22, items: ['albedo', 'i14', 'raiden', 'astra'], speed: -0.72, scale: 1.0 },
  { y: 80, x: -14, items: ['i14', 'raiden', 'astra', 'albedo'], speed: 0.86, scale: 0.92 },
];

export default function SceneLibrary({ t, global, variant = 0 }) {
  const head = easeOutQuint(seg(t, 0.1, 1.0));

  // The wall drifts. Each row moves at its own rate and in its own direction, so the
  // wall reads as depth rather than as a flat grid - and it is never still.
  const drift = (r) => (t * 22 * r.speed) % 480;

  const count = easeOut(seg(t, 1.0, 1.9));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={0.8} warmSide={variant ? 'left' : 'right'} grid={false} />

      {/* ── the wall ──────────────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          // Pushed right and down so the copy has a clear column on the left.
          transform: 'translate3d(26%, 4%, 0) rotate(-7deg) scale(1.35)',
          transformOrigin: '50% 50%',
        }}
      >
        {ROWS.map((r, ri) => (
          <div
            key={ri}
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: `${r.y}%`,
              display: 'flex',
              gap: 26,
              transform: `translateX(${drift(r)}px)`,
            }}
          >
            {/* The row is drawn twice so the drift wraps without a gap. */}
            {[0, 1].map((pass) =>
              r.items.map((clip, i) => {
                const k = easeOut(seg(t, 0.35 + (ri * 4 + i) * 0.09, 1.05 + (ri * 4 + i) * 0.09));
                return (
                  <div
                    key={`${pass}-${i}`}
                    style={{
                      flexShrink: 0,
                      width: 480 * r.scale,
                      borderRadius: 12,
                      overflow: 'hidden',
                      opacity: 0.30 + 0.70 * k,
                      transform: `translateY(${(1 - k) * 22}px) scale(${0.95 + 0.05 * k})`,
                      boxShadow: '0 30px 60px -30px rgba(0,0,0,.9)',
                      border: '1px solid rgba(255,255,255,.10)',
                    }}
                  >
                    <Wallpaper clip={clip} t={global} width="100%" radius={0} />
                  </div>
                );
              }),
            )}
          </div>
        ))}
      </div>

      {/* ── the scrim and the copy ────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(96deg, rgba(6,7,10,.94) 0%, rgba(6,7,10,.82) 26%, rgba(6,7,10,.30) 52%, rgba(6,7,10,.34) 100%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: 116,
          top: '50%',
          transform: 'translateY(-50%)',
          maxWidth: 660,
        }}
      >
        <Eyebrow color="#a06bff" style={{ marginBottom: 20, opacity: head }}>
          Pustaka
        </Eyebrow>
        <Type size={58} style={{ opacity: head, transform: `translateY(${(1 - head) * 22}px)` }}>
          Ribuan wallpaper,
          <br />
          semuanya hidup.
        </Type>
        <div
          style={{
            marginTop: 28,
            fontFamily: FONT,
            fontSize: 23,
            lineHeight: 1.5,
            color: '#b8bec7',
            maxWidth: 540,
            opacity: easeOut(seg(t, 0.7, 1.5)),
          }}
        >
          Setiap pratinjau di pustaka berjalan sungguhan — bukan gambar diam.
        </div>

        <div
          style={{
            marginTop: 36,
            display: 'flex',
            gap: 44,
            opacity: count,
            transform: `translateY(${(1 - count) * 18}px)`,
          }}
        >
          {[
            { n: '5.000+', l: 'wallpaper' },
            { n: '4K', l: 'siap pakai' },
            { n: '0', l: 'langganan' },
          ].map((s) => (
            <div key={s.l}>
              <div style={{ fontFamily: FONT, fontSize: 38, fontWeight: 800, letterSpacing: '-.03em', color: '#fff' }}>
                {s.n}
              </div>
              <div style={{ fontFamily: FONT, fontSize: 17, color: '#8d939c', marginTop: 4 }}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
