// SceneMonitors — three monitors, each playing a different wallpaper.
//
// The wallpapers are genuinely moving: the frames come from the real clips the
// app ships, driven by the render clock so they play smoothly and reproducibly.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import WallpaperStage from '../WallpaperStage.jsx';
import { seg, easeOut, easeOutQuint, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

const MONITORS = [
  { clip: 'raiden', label: 'DISPLAY 1', delay: 0.7, depth: 0.55 },
  { clip: 'astra',  label: 'DISPLAY 2', delay: 1.0, depth: 0.8 },
  { clip: 'albedo', label: 'DISPLAY 3', delay: 1.3, depth: 1.05 },
];

export default function SceneMonitors({ t, global }) {
  const head = parallax(global, TOTAL, 0.95, 26);
  const bg = parallax(global, TOTAL, 0.26, 44);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* The three monitors are the subject; this is a fourth wallpaper far
          behind them, so the beat is not floating on black. */}
      <div
        style={{
          position: 'absolute',
          inset: '-6%',
          opacity: 0.42,
          transform: `translate3d(${bg.x}px, ${bg.y}px, 0) scale(${1.12 * bg.scale})`,
        }}
      >
        <WallpaperStage clip="i14" t={global} offset={5} mode="fill" width="100%" radius={0} />
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(80% 70% at 50% 50%, rgba(7,7,10,.58) 0%, rgba(7,7,10,.80) 100%)',
        }}
      />
      <Aurora t={t} accent="#3ad0e0" intensity={0.13} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 42,
        }}
      >
        <div
          style={{
            textAlign: 'center',
            transform: `translate3d(${head.x}px, ${head.y}px, 0)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: 14,
              fontWeight: 700,
              letterSpacing: '.22em',
              textTransform: 'uppercase',
              color: '#3ad0e0',
              marginBottom: 16,
              opacity: seg(t, 0, 0.5),
            }}
          >
            Multi-monitor
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 60,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-.035em',
              color: '#fff',
            }}
          >
            <SplitText text="Beda layar, beda wallpaper." t={t} delay={0.1} stagger={0.024} y={36} />
          </div>
          <div
            style={{
              marginTop: 16,
              fontFamily: FONT,
              fontSize: 22,
              color: '#a8aeb8',
              opacity: seg(t, 0.9, 1.6),
              transform: `translateY(${(1 - easeOut(seg(t, 0.9, 1.6))) * 16}px)`,
            }}
          >
            Tiap monitor punya pengaturannya sendiri, dan susunannya bisa disimpan.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 34, marginTop: 6 }}>
          {MONITORS.map((m) => {
            const k = easeOutQuint(seg(t, m.delay, m.delay + 0.9));
            const p = parallax(global, TOTAL, m.depth, 30);
            return (
              <div
                key={m.label}
                style={{
                  position: 'relative',
                  opacity: seg(t, m.delay, m.delay + 0.4),
                  transform: `translate3d(${p.x}px, ${p.y + (1 - k) * 70}px, 0)
                              scale(${(0.88 + 0.12 * k) * p.scale})`,
                }}
              >
                <WallpaperStage clip={m.clip} t={global} offset={m.delay} mode="monitor" width={430} />
                <div
                  style={{
                    marginTop: 18,
                    textAlign: 'center',
                    fontFamily: FONT,
                    // Readable at 1080p on a phone, and measured rather than judged:
                    // tools/check-promo-text.py reported this label at 14px with a
                    // contrast of 1.96 against the wallpaper behind it, which is a
                    // failure at any size. It is now 24px (the point where the
                    // threshold drops to 3.0) and carries a shadow that separates it
                    // from whatever is behind.
                    fontSize: 24,
                    fontWeight: 700,
                    letterSpacing: '.12em',
                    color: '#ffffff',
                    textShadow: '0 2px 12px rgba(0,0,0,.9), 0 0 30px rgba(0,0,0,.7)',
                  }}
                >
                  {m.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
