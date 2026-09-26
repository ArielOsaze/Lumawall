// SceneProblem — the CPU comparison, told as a race rather than a static chart.
//
// The two bars grow from zero at the same moment, so the viewer watches one shoot
// up while the other barely moves. Same data as before, but the comparison is
// felt rather than read.

import React from 'react';
import SplitText from '../SplitText.jsx';
import CountUp from '../CountUp.jsx';
import BrandStage from '../BrandStage.jsx';
import { seg, easeOut, easeOutExpo, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

function Bar({ t, delay, to, max, color, label, sub, suffix = '%', decimals = 0 }) {
  const k = easeOutExpo(seg(t, delay, delay + 1.5));
  const width = (to / max) * 100 * k;
  const bad = color === '#ff3b57';

  // No per-bar parallax. The two bars carried different depths (1.0 and 0.7), so the
  // camera's drift moved them apart by a few dozen pixels - and a comparison whose
  // two halves slide relative to each other misreads the thing it is comparing. The
  // bars have to stay on a common axis.
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
            fontFamily: FONT,
            fontSize: 21,
            fontWeight: 600,
            color: '#c3c8d0',
            opacity: seg(t, delay - 0.2, delay + 0.3),
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: FONT,
            fontSize: 48,
            fontWeight: 800,
            letterSpacing: '-.03em',
            color,
            lineHeight: 1,
          }}
        >
          <CountUp to={to} t={t} delay={delay} dur={1.5} decimals={decimals} suffix={suffix} />
        </span>
      </div>

      <div
        style={{
          height: 20,
          borderRadius: 10,
          background: 'rgba(255,255,255,.05)',
          border: '1px solid rgba(255,255,255,.08)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${width}%`,
            borderRadius: 10,
            background: bad
              ? 'linear-gradient(90deg,#5c1a20,#ff3b57)'
              : 'linear-gradient(90deg,#155e3b,#35e07a)',
          }}
        />
      </div>

      <div
        style={{
          marginTop: 12,
          fontFamily: FONT,
          // 15px was 1.4% of the frame height - the smallest text in the piece, on
          // the shot that carries the product's central claim. This is the line
          // that explains WHY the two numbers differ, so it has to be read, not
          // just seen.
          fontSize: 18,
          color: '#c3cad2',
          opacity: seg(t, delay + 0.4, delay + 0.9),
        }}
      >
        {sub}
      </div>
    </div>
  );
}

export default function SceneProblem({ t, global }) {
  const head = parallax(global, TOTAL, 0.9, 30);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* The brand surface, not a wallpaper. This beat is about a number, and a
          wallpaper behind a number says nothing while costing the wallpaper its
          impact when it does appear later. */}
      <BrandStage t={global} intensity={1.15} warmSide="left" />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 150px',
          gap: 44,
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
              color: '#ff3b57',
              marginBottom: 16,
              opacity: seg(t, 0, 0.5),
            }}
          >
            Masalahnya
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 66,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-.035em',
              color: '#fff',
            }}
          >
            <SplitText text="Wallpaper video biasanya" t={t} delay={0.1} stagger={0.026} y={40} />
            <br />
            <SplitText text="makan CPU." t={t} delay={0.72} stagger={0.034} y={40} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 64, marginTop: 4 }}>
          {/* Both bars are measured on this machine, three 1080p30 wallpapers
              playing at once, and both are expressed as a share of ONE core so the
              comparison is like for like. The earlier pair (168% against 0.6%) was
              never measured: 168 came from the first version of the video, and the
              gap it drew was about eight times the real one. Software decode of
              these clips costs about 60% of one core; LumaWall costs about 11%. */}
          <Bar
            t={t}
            delay={1.35}
            to={60}
            max={60}
            color="#ff3b57"
            label="Tanpa LumaWall"
            sub="Software decode, semuanya di core CPU"
          />
          <Bar
            t={t}
            delay={2.05}
            to={11}
            max={60}
            color="#35e07a"
            label="Dengan LumaWall"
            sub="Hardware decode, ditangani blok GPU"
          />
        </div>

        <div
          style={{
            marginTop: 6,
            fontFamily: FONT,
            // Readable over a wallpaper rather than on flat colour: a busy image
            // reduces apparent contrast at the same measured ratio, and a review
            // of the render called this line too dim.
            fontSize: 25,
            color: '#d8dde3',
            textShadow: '0 2px 14px rgba(0,0,0,.7)',
            opacity: seg(t, 3.0, 3.75),
            transform: `translateY(${(1 - easeOut(seg(t, 3.0, 3.75))) * 20}px)`,
          }}
        >
          Yang mengerjakan bukan bagian yang sama.
        </div>
      </div>
    </div>
  );
}
