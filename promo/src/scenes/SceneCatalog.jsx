// SceneCatalog — the real app UI, in motion.
//
// The old version placed a screenshot on screen and cross-faded it. Here the
// screenshot sits in a frame that tilts in, the wallpaper grid scrolls inside it,
// and a cursor travels across it and clicks — so the viewer sees the product being
// used rather than a picture of the product.
//
// The screenshot is the genuine capture from the running application.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import { seg, easeOut, easeInOut } from '../anim.js';

export default function SceneCatalog({ t, dur }) {

  // Frame entrance.
  const enter = easeOut(seg(t, 0.35, 1.5));

  // The screenshot slides up inside the frame, as if the grid were scrolling, and
  // the frame itself pushes in very slowly. Two independent motions keep the
  // section alive for its full length instead of settling into a still image.
  const scrollY = -easeInOut(seg(t, 1.0, dur - 0.4)) * 96;
  const push = 1 + 0.045 * seg(t, 0.9, dur);

  // Cursor: travels in, hovers a card, clicks it.
  const travel = easeOut(seg(t, 0.9, 1.9));
  const cx = 250 + travel * 340;
  const cy = 470 + Math.sin(t * 1.1) * 26 - travel * 60;
  const clickAt = 2.05;
  const clicking = t > clickAt && t < clickAt + 0.22;
  const ripple = seg(t, clickAt, clickAt + 0.75);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} intensity={0.2} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 110px',
          gap: 62,
        }}
      >
        {/* Left: the message */}
        <div style={{ width: 560, flexShrink: 0 }}>
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
            Katalog
          </div>
          <div
            style={{
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 56,
              fontWeight: 700,
              lineHeight: 1.12,
              letterSpacing: '-.02em',
              color: '#fff',
            }}
          >
            <SplitText text="5.000+ wallpaper" t={t} delay={0.15} stagger={0.028} y={38} />
            <br />
            <SplitText text="siap pakai." t={t} delay={0.78} stagger={0.036} y={38} />
          </div>
          <div
            style={{
              marginTop: 24,
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 23,
              lineHeight: 1.5,
              color: '#a8adb6',
              maxWidth: 500,
              opacity: seg(t, 1.35, 2.1),
              transform: `translateY(${(1 - easeOut(seg(t, 1.35, 2.1))) * 18}px)`,
            }}
          >
            Cari, filter, unduh, lalu terapkan — semuanya di dalam aplikasi. Tanpa
            buka browser, tanpa cari file manual.
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 26, flexWrap: 'wrap' }}>
            {['Anime Loop', 'Dynamic', 'Landscape', '4K'].map((c, i) => {
              const k = seg(t, 1.6 + i * 0.09, 2.1 + i * 0.09);
              const e = easeOut(k);
              return (
                <span
                  key={c}
                  style={{
                    fontFamily: '"Cascadia Mono", Consolas, monospace',
                    fontSize: 13,
                    color: '#cfd2d8',
                    border: '1px solid rgba(255,255,255,.11)',
                    background: 'rgba(255,255,255,.03)',
                    borderRadius: 999,
                    padding: '7px 15px',
                    opacity: e,
                    transform: `translateY(${(1 - e) * 14}px)`,
                  }}
                >
                  {c}
                </span>
              );
            })}
          </div>
        </div>

        {/* Right: the real UI, in motion */}
        <div
          style={{
            position: 'relative',
            flex: 1,
            height: 700,
            borderRadius: 16,
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,.11)',
            boxShadow: '0 40px 90px -30px rgba(0,0,0,.9), 0 0 0 1px rgba(255,255,255,.03)',
            background: '#0c0c10',
            opacity: enter,
            transform: `translateY(${(1 - enter) * 46}px) rotateX(${(1 - enter) * 9}deg) scale(${(0.95 + 0.05 * enter) * push})`,
            transformOrigin: 'center bottom',
            perspective: 1200,
          }}
        >
          <img
            src="./shots/ui-discover.png"
            alt=""
            style={{
              position: 'absolute',
              top: scrollY,
              left: 0,
              width: '100%',
              display: 'block',
            }}
          />

          {/* Cursor */}
          <div
            style={{
              position: 'absolute',
              left: cx,
              top: cy,
              width: 22,
              height: 22,
              opacity: t > 0.9 ? 1 : 0,
              transform: `scale(${clicking ? 0.86 : 1})`,
              filter: 'drop-shadow(0 2px 6px rgba(0,0,0,.7))',
            }}
          >
            <svg viewBox="0 0 24 24" width="22" height="22">
              <path d="M5 2l14 9-6 1.4L16 20l-3 1-3-7-5 4z" fill="#fff" stroke="#111" strokeWidth="1.1" />
            </svg>
          </div>

          {/* Click ripple */}
          {ripple > 0 && ripple < 1 && (
            <div
              style={{
                position: 'absolute',
                left: cx + 6,
                top: cy + 6,
                width: 18 + ripple * 78,
                height: 18 + ripple * 78,
                marginLeft: -(18 + ripple * 78) / 2,
                marginTop: -(18 + ripple * 78) / 2,
                borderRadius: '50%',
                border: `2px solid rgba(226,69,74,${(1 - ripple) * 0.85})`,
              }}
            />
          )}

          <div
            style={{
              position: 'absolute',
              inset: 0,
              pointerEvents: 'none',
              background:
                'linear-gradient(180deg, rgba(255,255,255,.055) 0%, transparent 14%, transparent 86%, rgba(0,0,0,.32) 100%)',
            }}
          />
        </div>
      </div>
    </div>
  );
}
