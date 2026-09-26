// SceneProblem — what a live wallpaper normally costs you.
//
// ── why the promo opens its argument here ───────────────────────────────────
//
// The previous version made this point with a headline and a screenshot of a CPU
// graph. A screenshot of a graph is a claim. The claim here is a number, and a number
// is only convincing if you watch it being measured - so this scene runs a live
// readout that climbs while you look at it.
//
// The shape of the argument: a task manager, drawn as UI rather than as a picture of
// UI, with the wallpaper process climbing. It ends high and stays high, and the scene
// cuts on that. The next scene is the product. That cut is the commercial's turn.
//
// Nothing here is a screenshot, so nothing here can be cropped.

import React from 'react';
import { t as tx } from '../copy.js';
import { Surface, Type, Eyebrow, Figure, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, easeOutExpo, loop } from '../anim.js';

const ROWS = [
  { name: tx('Wallpaper engine'), cpu: 41.2, mem: 1.24, hot: true },
  { name: tx('Browser'), cpu: 8.4, mem: 2.10, hot: false },
  { name: tx('Explorer'), cpu: 2.1, mem: 0.42, hot: false },
  { name: tx('Spotify'), cpu: 1.6, mem: 0.38, hot: false },
];

export default function SceneProblem({ t, global }) {
  const head = easeOutQuint(seg(t, 0.1, 0.9));

  // The readout climbs over the shot. It settles near its value and then keeps
  // twitching, so the number reads as live rather than as a printed figure.
  const climb = easeOutExpo(seg(t, 0.5, 2.6));
  const jitter = Math.sin(t * 9.3) * 0.5 + Math.sin(t * 21.7) * 0.28;

  const body = easeOut(seg(t, 0.8, 1.7));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.25} warmSide="left" />

      {/* A hot wash from the bottom-left, so the frame itself reads as "loaded". */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(70% 60% at 16% 88%, rgba(255,46,67,.20) 0%, rgba(255,46,67,0) 68%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 84,
          padding: '0 120px',
        }}
      >
        {/* ── the statement ─────────────────────────────────────────────────── */}
        <div style={{ width: 560, flexShrink: 0 }}>
          <Eyebrow style={{ marginBottom: 22, opacity: head }}>{tx('Masalahnya')}</Eyebrow>
          <Type size={56} style={{ opacity: head, transform: `translateY(${(1 - head) * 26}px)` }}>
            {tx('Wallpaper hidup')}
            <br />
            {tx('biasanya makan')}
            <br />
            <span style={{ color: '#ff3b57' }}>{tx('CPU.')}</span>
          </Type>
          <div
            style={{
              marginTop: 28,
              fontFamily: FONT,
              fontSize: 22,
              lineHeight: 1.55,
              color: '#a8aeb8',
              maxWidth: 520,
              opacity: body,
            }}
          >
            {tx('Animasi diproses di prosesor, laptop jadi panas, kipas berisik, baterai cepat habis.')}
          </div>
        </div>

        {/* ── the readout, drawn rather than screenshotted ──────────────────── */}
        <div
          style={{
            // A fixed width rather than `flex: 1`, so the readout cannot grow until its
            // right column runs off the frame. A review of the previous render found
            // the window cropped at the right edge, and `flex: 1` in a 1920 frame with
            // a 640px sibling was the reason.
            width: 900,
            flexShrink: 0,
            opacity: body,
            transform: `translateY(${(1 - body) * 40}px)`,
          }}
        >
          <div
            style={{
              borderRadius: 16,
              border: '1px solid rgba(255,255,255,.10)',
              background: 'rgba(12,13,17,.86)',
              boxShadow: '0 50px 110px -40px rgba(0,0,0,.95)',
              overflow: 'hidden',
            }}
          >
            {/* The window's title bar. */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '15px 20px',
                borderBottom: '1px solid rgba(255,255,255,.07)',
                background: 'rgba(255,255,255,.022)',
              }}
            >
              {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
                <span key={c} style={{ width: 11, height: 11, borderRadius: '50%', background: c }} />
              ))}
              <span style={{ marginLeft: 12, fontFamily: FONT, fontSize: 15, color: '#8d939c' }}>{tx('Task Manager — CPU')}</span>
            </div>

            {/* A big figure and a live trace. */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 26, padding: '26px 24px 20px' }}>
              <Figure
                to={41.2 + jitter}
                t={climb}
                dur={0.01}
                decimals={1}
                suffix="%"
                color="#ff3b57"
                size={78}
              />
              <div style={{ paddingBottom: 10 }}>
                <div style={{ fontFamily: FONT, fontSize: 17, color: '#8d939c' }}>{tx('Wallpaper engine')}</div>
                <div style={{ fontFamily: FONT, fontSize: 15, color: '#5f6670' }}>{tx('1 proses · 12 utas')}</div>
              </div>
            </div>

            {/* The trace: a line that climbs and keeps twitching. */}
            <div style={{ position: 'relative', height: 92, margin: '0 24px 22px', borderRadius: 8, background: 'rgba(255,46,67,.06)', border: '1px solid rgba(255,46,67,.16)', overflow: 'hidden' }}>
              <svg viewBox="0 0 400 92" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                <path
                  d={(() => {
                    // A rising line with a live wobble, clipped to how far the climb
                    // has got, so the graph is drawn by the same clock as the figure.
                    const pts = [];
                    for (let i = 0; i <= 40; i++) {
                      const p = i / 40;
                      const vis = climb >= p;
                      const v = (0.28 + 0.62 * p + Math.sin(p * 22) * 0.045) * (vis ? 1 : 0.28 + 0.62 * climb);
                      pts.push(`${(p * 400).toFixed(1)},${(92 - v * 86).toFixed(1)}`);
                    }
                    return `M${pts.join(' L')}`;
                  })()}
                  fill="none"
                  stroke="#ff3b57"
                  strokeWidth="2.5"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>
            </div>

            {/* The process list, so the readout is a system rather than one number. */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,.07)' }}>
              {ROWS.map((r, i) => {
                const k = easeOut(seg(t, 1.1 + i * 0.13, 1.7 + i * 0.13));
                const cpu = r.hot ? r.cpu * climb + (r.hot ? jitter : 0) : r.cpu;
                return (
                  <div
                    key={r.name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '13px 24px',
                      borderBottom: i < ROWS.length - 1 ? '1px solid rgba(255,255,255,.05)' : 'none',
                      opacity: k,
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 2,
                        background: r.hot ? '#ff3b57' : '#4a5058',
                        marginRight: 14,
                      }}
                    />
                    <span
                      style={{
                        flex: 1,
                        fontFamily: FONT,
                        fontSize: 19,
                        fontWeight: r.hot ? 700 : 400,
                        color: r.hot ? '#fff' : '#9aa0a9',
                      }}
                    >
                      {r.name}
                    </span>
                    <span
                      style={{
                        fontFamily: FONT,
                        fontSize: 19,
                        fontWeight: r.hot ? 700 : 400,
                        color: r.hot ? '#ff3b57' : '#8d939c',
                        fontVariantNumeric: 'tabular-nums',
                        width: 92,
                        textAlign: 'right',
                      }}
                    >
                      {cpu.toFixed(1)}%
                    </span>
                    <span
                      style={{
                        fontFamily: FONT,
                        fontSize: 17,
                        color: '#5f6670',
                        fontVariantNumeric: 'tabular-nums',
                        width: 108,
                        textAlign: 'right',
                      }}
                    >
                      {r.mem.toFixed(2)} GB
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
