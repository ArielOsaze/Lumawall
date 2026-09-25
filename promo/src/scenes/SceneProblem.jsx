// SceneProblem — the CPU comparison, told as a race.
//
// The old version put two static numbers on screen. Here both bars grow from zero
// at the same moment, so the viewer watches one shoot up while the other barely
// moves. Same data, but the comparison is felt rather than read.
//
// Every value is a pure function of `t`.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import CountUp from '../CountUp.jsx';
import { seg, easeOut, easeOutExpo } from '../anim.js';

function Bar({ t, delay, to, max, color, label, sub, suffix = '%', decimals = 0 }) {
  const k = easeOutExpo(seg(t, delay, delay + 1.5));
  const width = (to / max) * 100 * k;
  const bad = color === '#e2454a';

  return (
    <div style={{ flex: 1 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 14,
        }}
      >
        <span
          style={{
            fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
            fontSize: 22,
            color: '#cfd2d8',
            opacity: seg(t, delay - 0.2, delay + 0.3),
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: '"Cascadia Mono", Consolas, monospace',
            fontSize: 44,
            fontWeight: 700,
            color,
            lineHeight: 1,
            textShadow: `0 0 28px ${color}66`,
          }}
        >
          <CountUp to={to} t={t} delay={delay} dur={1.5} decimals={decimals} suffix={suffix} />
        </span>
      </div>

      <div
        style={{
          height: 22,
          borderRadius: 11,
          background: 'rgba(255,255,255,.05)',
          border: '1px solid rgba(255,255,255,.08)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${width}%`,
            borderRadius: 11,
            background: bad
              ? 'linear-gradient(90deg,#7a1f22,#e2454a)'
              : 'linear-gradient(90deg,#1f7a4d,#35e07a)',
            boxShadow: `0 0 22px -4px ${color}`,
          }}
        />
      </div>

      <div
        style={{
          marginTop: 12,
          fontFamily: '"Cascadia Mono", Consolas, monospace',
          fontSize: 14,
          color: '#7d838d',
          opacity: seg(t, delay + 0.4, delay + 0.9),
        }}
      >
        {sub}
      </div>
    </div>
  );
}

export default function SceneProblem({ t, dur }) {

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
      }}
    >
      <Aurora t={t} accent="#e2454a" accent2="#e2454a" intensity={0.22} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 150px',
          gap: 46,
        }}
      >
        <div>
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
            Masalahnya
          </div>
          <div
            style={{
              fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
              fontSize: 62,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-.02em',
              color: '#fff',
            }}
          >
            <SplitText text="Wallpaper video biasanya" t={t} delay={0.1} stagger={0.026} y={40} />
            <br />
            <SplitText text="makan CPU." t={t} delay={0.72} stagger={0.034} y={40} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 68, marginTop: 6 }}>
          <Bar
            t={t}
            delay={1.35}
            to={168}
            max={168}
            color="#e2454a"
            label="Tanpa LumaWall"
            sub="Software decode — semua di core CPU"
          />
          <Bar
            t={t}
            delay={2.05}
            to={0.6}
            max={168}
            color="#35e07a"
            label="Dengan LumaWall"
            sub="Hardware decode — ditangani blok GPU"
            decimals={1}
          />
        </div>

        <div
          style={{
            marginTop: 8,
            fontFamily: 'Bahnschrift, "Segoe UI", sans-serif',
            fontSize: 24,
            color: '#c8ccd4',
            opacity: seg(t, 3.0, 3.75),
            transform: `translateY(${(1 - easeOut(seg(t, 3.0, 3.75))) * 20}px)`,
          }}
        >
          Selisihnya bukan sedikit — ini bedanya CPU vs chip grafis.
        </div>
      </div>
    </div>
  );
}
