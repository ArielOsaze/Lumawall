// ScenePerf — the measured numbers, counted up.
//
// The old version showed the performance screenshot as a static card. Here three
// real measured figures count up one after another, so the claims are backed by
// something moving on screen.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import CountUp from '../CountUp.jsx';
import { seg, easeOut } from '../anim.js';

function Stat({ t, label, to, decimals, suffix, color, delay, sub }) {
  const k = easeOut(seg(t, delay, delay + 0.7));
  return (
    <div
      style={{
        flex: 1,
        padding: '22px 24px',
        borderRadius: 13,
        border: '1px solid rgba(255,255,255,.09)',
        background: 'rgba(255,255,255,.028)',
        opacity: k,
        transform: `translateY(${(1 - k) * 26}px)`,
      }}
    >
      <div
        style={{
          fontFamily: '"Cascadia Mono", Consolas, monospace',
          fontSize: 12,
          letterSpacing: '.2em',
          color: '#7d838d',
          textTransform: 'uppercase',
          marginBottom: 12,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: '"Cascadia Mono", Consolas, monospace',
          fontSize: 40,
          fontWeight: 700,
          color,
          lineHeight: 1,
          textShadow: `0 0 26px ${color}44`,
        }}
      >
        <CountUp to={to} t={t} delay={delay} dur={1.3} decimals={decimals} suffix={suffix} />
      </div>
      <div
        style={{
          marginTop: 10,
          fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
          fontSize: 14.5,
          color: '#8b9099',
        }}
      >
        {sub}
      </div>
    </div>
  );
}

export default function ScenePerf({ t, dur }) {
  // A slow push so the numbers keep moving even after they have counted up.
  const push = 1 + 0.03 * seg(t, 0, dur);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} accent="#3ad0e0" intensity={0.18} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 130px',
          gap: 40,
          transform: `scale(${push})`,
        }}
      >
        <div>
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
            Terukur
          </div>
          <div
            style={{
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 56,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-.02em',
              color: '#fff',
            }}
          >
            <SplitText text="Angkanya, bukan klaim." t={t} delay={0.1} stagger={0.026} y={36} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 20 }}>
          <Stat t={t} label="CPU" to={0.6} decimals={1} suffix="%" color="#35e07a" delay={0.7}
                sub="Tiga wallpaper 1080p bersamaan" />
          <Stat t={t} label="RAM" to={169} decimals={0} suffix=" MB" color="#3ad0e0" delay={0.85}
                sub="Seluruh proses, tiga monitor" />
          <Stat t={t} label="Resume" to={141} decimals={0} suffix=" ms" color="#e2454a" delay={1.0}
                sub="Dari game ditutup ke animasi jalan" />
        </div>

        <div
          style={{
            marginTop: 6,
            padding: '18px 22px',
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,.08)',
            background: 'rgba(255,255,255,.02)',
            fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
            fontSize: 19,
            color: '#a8adb6',
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
