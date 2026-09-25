// ScenePerf — the measured numbers, with a wallpaper playing behind them.
//
// The statistics are the claim; the wallpaper behind them is the evidence that
// the app is doing something while those numbers are true.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import CountUp from '../CountUp.jsx';
import WallpaperStage from '../WallpaperStage.jsx';
import { seg, easeOut, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

function Stat({ t, label, to, decimals, suffix, color, delay, sub, depth }) {
  const k = easeOut(seg(t, delay, delay + 0.7));
  const p = parallax(t + delay, TOTAL, depth, 30);

  return (
    <div
      style={{
        flex: 1,
        padding: '22px 24px',
        borderRadius: 13,
        border: '1px solid rgba(255,255,255,.09)',
        background: 'rgba(255,255,255,.028)',
        opacity: k,
        transform: `translate3d(${p.x}px, ${p.y + (1 - k) * 26}px, 0)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: '.16em',
          color: '#7a838c',
          textTransform: 'uppercase',
          marginBottom: 12,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 42,
          fontWeight: 800,
          letterSpacing: '-.03em',
          color,
          lineHeight: 1,
        }}
      >
        <CountUp to={to} t={t} delay={delay} dur={1.3} decimals={decimals} suffix={suffix} />
      </div>
      <div style={{ marginTop: 10, fontFamily: FONT, fontSize: 15, color: '#8b9099' }}>{sub}</div>
    </div>
  );
}

export default function ScenePerf({ t, global }) {
  const head = parallax(global, TOTAL, 0.95, 26);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* A wallpaper playing behind the numbers, heavily dimmed, so even the
          statistics beat shows the product working. */}
      <div style={{ position: 'absolute', inset: '-5%', opacity: 0.46 }}>
        <WallpaperStage clip="astra" t={global} offset={4} mode="fill" width="100%" radius={0} />
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(7,7,10,.76) 0%, rgba(7,7,10,.84) 50%, rgba(7,7,10,.78) 100%)',
        }}
      />
      <Aurora t={t} accent="#3ad0e0" intensity={0.15} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 130px',
          gap: 38,
        }}
      >
        <div style={{ transform: `translate3d(${head.x}px, ${head.y}px, 0)` }}>
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
            Terukur
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
            <SplitText text="Angkanya, bukan klaim." t={t} delay={0.1} stagger={0.026} y={36} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 20 }}>
          <Stat t={t} label="CPU" to={0.6} decimals={1} suffix="%" color="#35e07a" delay={0.7}
                sub="Tiga wallpaper 1080p bersamaan" depth={1.0} />
          <Stat t={t} label="RAM" to={169} decimals={0} suffix=" MB" color="#3ad0e0" delay={0.85}
                sub="Seluruh proses, tiga monitor" depth={0.8} />
          <Stat t={t} label="Resume" to={141} decimals={0} suffix=" ms" color="#ff3b57" delay={1.0}
                sub="Dari game ditutup sampai jalan lagi" depth={0.6} />
        </div>

        <div
          style={{
            marginTop: 4,
            padding: '18px 22px',
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,.08)',
            background: 'rgba(255,255,255,.02)',
            fontFamily: FONT,
            fontSize: 19,
            color: '#a8aeb8',
            opacity: seg(t, 1.5, 2.2),
            transform: `translateY(${(1 - easeOut(seg(t, 1.5, 2.2))) * 18}px)`,
          }}
        >
          Wallpaper statis dirender langsung, bukan lewat WebView — hemat sekitar
          130 MB RAM per monitor.
        </div>
      </div>
    </div>
  );
}
