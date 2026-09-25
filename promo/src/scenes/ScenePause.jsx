// ScenePause — the auto-pause feature, animated as a before/after.
//
// The old version showed a label and a still. Here a window physically grows to
// cover the screen, the wallpaper underneath freezes and desaturates, a GPU meter
// drops to zero, then the window closes and everything springs back. The point of
// the feature - "it stops costing you anything when you are not looking at it" -
// is shown rather than asserted.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import { seg, easeOut, easeOutExpo, loop } from '../anim.js';

export default function ScenePause({ t, dur }) {

  // The window opens at 1.1s, covers by 1.75s, closes at 5.2s.
  const openK = easeOutExpo(seg(t, 1.1, 1.75));
  const closeK = easeOutExpo(seg(t, 5.2, 5.8));
  const cover = openK * (1 - closeK);
  const covered = cover > 0.985;
  const coverW = cover * 100;
  const coverH = cover * 100;

  // The GPU figure follows the cover state, with a short settle so it reads as a
  // measurement rather than a jump cut.
  const dropK = easeOut(seg(t, 1.85, 2.5));
  const riseK = easeOut(seg(t, 5.4, 6.0));
  const gpu = 21 - 21 * dropK + 21 * riseK;
  const gpuGood = gpu < 10.5;

  // The wallpaper keeps moving while visible and holds still while covered. Two
  // sine waves at different periods keep the motion from reading as a loop.
  const wiggle = covered ? 0 : Math.sin(t * 0.9) * 7 + Math.sin(t * 0.37) * 4;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} accent="#e2454a" accent2="#3ad0e0" intensity={0.21} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 120px',
          gap: 70,
        }}
      >
        <div style={{ width: 520, flexShrink: 0 }}>
          <div
            style={{
              fontFamily: '"Cascadia Mono", Consolas, monospace',
              fontSize: 15,
              letterSpacing: '.34em',
              textTransform: 'uppercase',
              color: '#e2454a',
              marginBottom: 16,
              opacity: seg(t, 0, 0.5),
            }}
          >
            Pause otomatis
          </div>
          <div
            style={{
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 54,
              fontWeight: 700,
              lineHeight: 1.12,
              letterSpacing: '-.02em',
              color: '#fff',
            }}
          >
            <SplitText text="Berhenti sendiri" t={t} delay={0.15} stagger={0.028} y={36} />
            <br />
            <SplitText text="saat tak terlihat." t={t} delay={0.85} stagger={0.032} y={36} />
          </div>
          <div
            style={{
              marginTop: 24,
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 22,
              lineHeight: 1.5,
              color: '#a8adb6',
              maxWidth: 470,
              opacity: seg(t, 1.5, 2.2),
              transform: `translateY(${(1 - easeOut(seg(t, 1.5, 2.2))) * 16}px)`,
            }}
          >
            Buka game fullscreen — wallpaper di layar itu berhenti, decode GPU turun
            ke nol. Tutup game, jalan lagi seketika.
          </div>

          <div
            style={{
              marginTop: 28,
              display: 'flex',
              alignItems: 'baseline',
              gap: 14,
              opacity: seg(t, 2.4, 2.9),
            }}
          >
            <span
              style={{
                fontFamily: '"Cascadia Mono", Consolas, monospace',
                fontSize: 13,
                letterSpacing: '.18em',
                color: '#7d838d',
                textTransform: 'uppercase',
              }}
            >
              Decode GPU
            </span>
            <span
              style={{
                fontFamily: '"Cascadia Mono", Consolas, monospace',
                fontSize: 40,
                fontWeight: 700,
                color: gpuGood ? '#35e07a' : '#e2454a',
                lineHeight: 1,
                textShadow: `0 0 26px ${gpuGood ? '#35e07a' : '#e2454a'}55`,
              }}
            >
              {Math.round(gpu)}%
            </span>
          </div>
        </div>

        {/* Right: the monitor, the wallpaper, and the covering window */}
        <div
          style={{
            position: 'relative',
            flex: 1,
            height: 640,
            opacity: easeOut(seg(t, 0.4, 1.4)),
            transform: `translateX(${(1 - easeOut(seg(t, 0.4, 1.4))) * 50}px)`,
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: 14,
              overflow: 'hidden',
              border: '2px solid #24262c',
              background: '#000',
              boxShadow: '0 40px 80px -30px rgba(0,0,0,.9)',
            }}
          >
            <img
              src="./shots/wallpaper-i14.png"
              alt=""
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `translateX(${wiggle}px) scale(1.06)`,
                filter: covered ? 'saturate(.25) brightness(.4)' : 'none',
              }}
            />

            {/* The application window growing over it */}
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                transform: 'translate(-50%,-50%)',
                width: `${coverW}%`,
                height: `${coverH}%`,
                background: '#0d0f13',
                borderRadius: coverW > 99 ? 0 : 12,
                border: coverW > 99 ? 'none' : '1px solid rgba(255,255,255,.12)',
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: coverW > 1 ? 1 : 0,
              }}
            >
              {coverW > 40 && (
                <div
                  style={{
                    textAlign: 'center',
                    fontFamily: '"Cascadia Mono", Consolas, monospace',
                    opacity: Math.max(0, (coverW - 55) / 45),
                  }}
                >
                  <div
                    style={{
                      fontSize: 15,
                      letterSpacing: '.3em',
                      color: '#7d838d',
                      textTransform: 'uppercase',
                    }}
                  >
                    Fullscreen app
                  </div>
                  <div
                    style={{
                      marginTop: 10,
                      fontSize: 27,
                      color: '#cfd2d8',
                      fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
                    }}
                  >
                    Wallpaper dijeda
                  </div>
                </div>
              )}
            </div>

            {/* PAUSED badge */}
            <div
              style={{
                position: 'absolute',
                top: 18,
                right: 18,
                fontFamily: '"Cascadia Mono", Consolas, monospace',
                fontSize: 12,
                letterSpacing: '.22em',
                color: '#35e07a',
                border: '1px solid rgba(53,224,122,.4)',
                background: 'rgba(53,224,122,.10)',
                borderRadius: 999,
                padding: '6px 14px',
                textTransform: 'uppercase',
                opacity: covered ? 1 : 0,
                transform: `scale(${covered ? 1 : 0.9})`,
              }}
            >
              Paused
            </div>

            {/* A live indicator that is only visible while the wallpaper runs */}
            {!covered && (
              <div
                style={{
                  position: 'absolute',
                  top: 18,
                  right: 18,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontFamily: '"Cascadia Mono", Consolas, monospace',
                  fontSize: 12,
                  letterSpacing: '.22em',
                  color: '#e2454a',
                  textTransform: 'uppercase',
                  opacity: seg(t, 0.6, 1.1) * (1 - seg(t, 1.75, 2.0)),
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: '#e2454a',
                    opacity: 0.4 + 0.6 * (loop(t, 1.4) < 0.5 ? 1 : 0),
                  }}
                />
                Running
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
