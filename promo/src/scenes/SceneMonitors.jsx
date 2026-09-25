// SceneMonitors — one wallpaper per display, shown by moving real wallpaper art
// into three monitor shapes.
//
// The old version drew three rectangles with labels. Here the wallpaper images
// physically fly into the monitor frames one after another, each slightly behind
// the last, so the feature is shown happening rather than stated.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import { seg, easeOut, easeOutBack } from '../anim.js';

const MONITORS = [
  { src: './shots/wallpaper-i14.png',     label: 'DISPLAY 1', delay: 0.85 },
  { src: './shots/wallpaper-raiden.png',  label: 'DISPLAY 2', delay: 1.15 },
  { src: './shots/wallpaper-acheron.png', label: 'DISPLAY 3', delay: 1.45 },
];

export default function SceneMonitors({ t, dur }) {
  // A slow camera push for the whole scene. Without it the middle of the video
  // sits still once the three monitors have arrived, which is what made the
  // earlier cut feel dry.
  const push = 1 + 0.035 * seg(t, 0, dur);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} accent="#3ad0e0" intensity={0.19} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 44,
          transform: `scale(${push})`,
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontFamily: '"Cascadia Mono", Consolas, monospace',
              fontSize: 15,
              letterSpacing: '.34em',
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
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 58,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-.02em',
              color: '#fff',
            }}
          >
            <SplitText text="Beda layar, beda wallpaper." t={t} delay={0.1} stagger={0.024} y={36} />
          </div>
          <div
            style={{
              marginTop: 16,
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 23,
              color: '#a8adb6',
              opacity: seg(t, 1.0, 1.7),
              transform: `translateY(${(1 - easeOut(seg(t, 1.0, 1.7))) * 16}px)`,
            }}
          >
            Tiap monitor diatur sendiri — termasuk profil yang bisa disimpan.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 34, marginTop: 6 }}>
          {MONITORS.map((m) => {
            const k = easeOutBack(seg(t, m.delay, m.delay + 0.8), 1.05);
            const ki = easeOut(seg(t, m.delay + 0.2, m.delay + 1.2));
            return (
              <div
                key={m.label}
                style={{
                  position: 'relative',
                  opacity: seg(t, m.delay, m.delay + 0.4),
                  transform: `translateY(${(1 - k) * 70}px) scale(${0.86 + 0.14 * k})`,
                }}
              >
                <div
                  style={{
                    width: 440,
                    height: 248,
                    borderRadius: 10,
                    overflow: 'hidden',
                    border: '2px solid #24262c',
                    background: '#000',
                    boxShadow: '0 30px 60px -24px rgba(0,0,0,.9)',
                  }}
                >
                  <img
                    src={m.src}
                    alt=""
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      display: 'block',
                      opacity: ki,
                      transform: `scale(${1.18 - 0.18 * ki})`,
                    }}
                  />
                </div>

                <div
                  style={{
                    width: 76,
                    height: 15,
                    margin: '0 auto',
                    background: 'linear-gradient(180deg,#2a2d34,#191b20)',
                    borderRadius: '0 0 5px 5px',
                  }}
                />
                <div
                  style={{
                    width: 168,
                    height: 8,
                    margin: '0 auto',
                    background: 'linear-gradient(180deg,#22242a,#15161a)',
                    borderRadius: 5,
                  }}
                />

                <div
                  style={{
                    marginTop: 13,
                    textAlign: 'center',
                    fontFamily: '"Cascadia Mono", Consolas, monospace',
                    fontSize: 13,
                    letterSpacing: '.16em',
                    color: '#7d838d',
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
