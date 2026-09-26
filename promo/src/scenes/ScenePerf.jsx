// ScenePerf — the measured numbers, with a wallpaper playing behind them.
//
// The statistics are the claim; the wallpaper behind them is the evidence that
// the app is doing something while those numbers are true.

import React from 'react';
import SplitText from '../SplitText.jsx';
import CountUp from '../CountUp.jsx';
import BrandStage from '../BrandStage.jsx';
import { seg, easeOut, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

function Stat({ t, label, to, decimals, suffix, color, delay, sub }) {
  const k = easeOut(seg(t, delay, delay + 0.7));

  // No parallax on these. Each card used to carry its own depth (1.0, 0.8, 0.6),
  // which meant the camera's leftward drift moved them by different amounts: the
  // CPU card travelled 132 px while the RAM card travelled 106, so the row came
  // apart and the first card was pushed off the left edge entirely - it was never
  // once fully visible in the finished render. These are measured figures; they
  // have to stay where they can be read.
  return (
    <div
      style={{
        flex: 1,
        padding: '22px 24px',
        borderRadius: 13,
        border: '1px solid rgba(255,255,255,.09)',
        background: 'rgba(255,255,255,.028)',
        opacity: k,
        transform: `translate3d(0, ${(1 - k) * 26}px, 0)`,
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
          // The figures ARE the claim. At 42px they were 3.9% of the frame height
          // - smaller than the headline above them, and easy to skim past in a
          // promo whose whole argument is how little this costs. 60px is 5.6%,
          // which makes each number the largest thing in its card.
          fontSize: 60,
          fontWeight: 800,
          letterSpacing: '-.035em',
          color,
          lineHeight: 1,
        }}
      >
        <CountUp to={to} t={t} delay={delay} dur={1.3} decimals={decimals} suffix={suffix} />
      </div>
      <div style={{ marginTop: 10, fontFamily: FONT, fontSize: 17, color: '#9aa0a9' }}>{sub}</div>
    </div>
  );
}

export default function ScenePerf({ t, global }) {
  const head = parallax(global, TOTAL, 0.95, 26);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* A wallpaper playing behind the numbers, heavily dimmed, so even the
          statistics beat shows the product working. */}
      {/* The brand surface: these are measured figures, and the figures are the
          only thing that should be competing for attention. */}
      <BrandStage t={global} intensity={1.1} warmSide="right" />

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
            <SplitText text="Angkanya dari pengukuran langsung." t={t} delay={0.1} stagger={0.026} y={36} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 20 }}>
          <Stat t={t} label="CPU" to={0.9} decimals={1} suffix="%" color="#35e07a" delay={0.7}
                sub="Dari 12 core, tiga wallpaper 1080p" />
          <Stat t={t} label="RAM" to={153} decimals={0} suffix=" MB" color="#3ad0e0" delay={0.85}
                sub="Seluruh proses, tiga monitor" />
          <Stat t={t} label="Resume" to={141} decimals={0} suffix=" ms" color="#ff3b57" delay={1.0}
                sub="Dari game ditutup sampai jalan lagi" />
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
          Wallpaper statis dirender langsung, bukan lewat WebView: hemat 75 MB
          RAM per monitor, diukur pada tiga layar.
        </div>
      </div>
    </div>
  );
}
