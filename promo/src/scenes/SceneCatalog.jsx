// SceneCatalog — the real app UI, in motion.
//
// The screenshot sits in a frame that pushes in on its own depth plane, the grid
// scrolls inside it, and a cursor travels across it and clicks — so the viewer
// sees the product being used rather than a picture of the product.

import React from 'react';
import SplitText from '../SplitText.jsx';
import BrandStage from '../BrandStage.jsx';
import { seg, easeOut, easeOutQuint, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

export default function SceneCatalog({ t, global }) {
  const enter = easeOutQuint(seg(t, 0.3, 1.5));
  const shot = parallax(global, TOTAL, 0.55, 38);
  const head = parallax(global, TOTAL, 0.95, 26);

  // The screenshot slides up inside its frame, as if the grid were scrolling.
  const scrollY = -easeOutQuint(seg(t, 0.9, 8.2)) * 110;

  // Cursor: travels in, hovers a card, clicks it.
  const travel = easeOutQuint(seg(t, 0.8, 1.9));
  const cx = 250 + travel * 330;
  const cy = 470 + Math.sin(t * 1.1) * 24 - travel * 56;
  const ripple = seg(t, 2.05, 2.8);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* The brand surface. The app window is the subject here, and a wallpaper
          behind it competed with the wallpapers inside it. */}
      <BrandStage t={global} intensity={1.0} warmSide="right" />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 110px',
          gap: 60,
        }}
      >
        <div
          style={{
            width: 545,
            flexShrink: 0,
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
              color: '#ff3b57',
              marginBottom: 16,
              opacity: seg(t, 0, 0.5),
            }}
          >
            Katalog
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 58,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-.035em',
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
              fontFamily: FONT,
              fontSize: 22,
              lineHeight: 1.55,
              color: '#a8aeb8',
              maxWidth: 490,
              opacity: seg(t, 1.35, 2.1),
              transform: `translateY(${(1 - easeOut(seg(t, 1.35, 2.1))) * 18}px)`,
            }}
          >
            Cari, filter, unduh, lalu terapkan — semuanya di dalam aplikasi. Tanpa buka
            browser, tanpa cari file manual.
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 26, flexWrap: 'wrap' }}>
            {['Anime Loop', 'Dynamic', 'Landscape', '4K'].map((c, i) => {
              const k = seg(t, 1.6 + i * 0.09, 2.1 + i * 0.09);
              const e = easeOut(k);
              return (
                <span
                  key={c}
                  style={{
                    fontFamily: FONT,
                    fontSize: 14,
                    fontWeight: 500,
                    color: '#c3c8d0',
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

        <div
          style={{
            position: 'relative',
            flex: 1,
            height: 700,
            borderRadius: 16,
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,.11)',
            boxShadow: '0 40px 90px -30px rgba(0,0,0,.9)',
            background: '#0c0c10',
            opacity: enter,
            transform: `translate3d(${shot.x}px, ${shot.y + (1 - enter) * 46}px, 0)
                        scale(${(0.95 + 0.05 * enter) * shot.scale})`,
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
              // The app's own screenshot has light-grey labels sitting on bright
              // artwork ("Selected wallpaper" over a purple glow), which measured
              // 1.43:1 in the render - unreadable. Dimming the screenshot slightly
              // and lifting its contrast fixes the label without changing the app's
              // appearance enough to misrepresent it.
              filter: 'brightness(0.88) contrast(1.12)',
            }}
          />

          <div
            style={{
              position: 'absolute',
              left: cx,
              top: cy,
              width: 22,
              height: 22,
              opacity: t > 0.85 ? 1 : 0,
              transform: `scale(${t > 2.05 && t < 2.27 ? 0.86 : 1})`,
              filter: 'drop-shadow(0 2px 6px rgba(0,0,0,.7))',
            }}
          >
            <svg viewBox="0 0 24 24" width="22" height="22">
              <path d="M5 2l14 9-6 1.4L16 20l-3 1-3-7-5 4z" fill="#fff" stroke="#111" strokeWidth="1.1" />
            </svg>
          </div>

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
                border: `2px solid rgba(255,59,87,${(1 - ripple) * 0.85})`,
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
