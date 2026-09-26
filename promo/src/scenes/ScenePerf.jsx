// ScenePerf — the same desktop, measured, before and after.
//
// ── what the previous version got wrong here ────────────────────────────────
//
// It showed two bars with two numbers and a caption. The numbers were the claim, but
// they were smaller than the headline above them, so the scene's actual evidence was
// the least prominent thing in the frame.
//
// The correction is that the figures ARE the scene. They are the largest type in the
// frame, they are measured against one shared axis so the comparison cannot misread,
// and the scene states where the readings came from - because an unlabelled number is
// an assertion and a labelled one is a measurement.
//
// There is no wallpaper in this scene at all. A scene about cost should not spend its
// frame on decoration.

import React from 'react';
import { t as tx } from '../copy.js';
import { Surface, Type, Eyebrow, Bar, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

export default function ScenePerf({ t, global, variant = 0 }) {
  const head = easeOutQuint(seg(t, 0.1, 0.9));
  const body = easeOut(seg(t, 0.45, 1.2));

  // The bars are on ONE scale: 41.2 is the other engine's reading, and 2.4 is this
  // product's. Both are drawn as a share of the larger, so the length of the second
  // bar is the actual difference.
  const MAX = 41.2;

  const foot = easeOut(seg(t, 2.3, 3.1));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={0.9} warmSide={variant ? 'right' : 'left'} grid={false} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 128px',
        }}
      >
        <div style={{ opacity: head, transform: `translateY(${(1 - head) * 20}px)` }}>
          <Eyebrow color="#35e07a" style={{ marginBottom: 18 }}>{tx('Hasil')}</Eyebrow>
          <Type size={56}>{tx('Beban CPU, diukur pada animasi yang sama.')}</Type>
        </div>

        <div style={{ marginTop: 52, display: 'flex', gap: 80, opacity: body }}>
          <div style={{ flex: 1 }}>
            <Bar
              t={t}
              delay={0.35}
              value={41.2}
              max={MAX}
              label={tx('Wallpaper engine biasa')}
              color="#ff3b57"
              suffix="%"
              decimals={1}
            />
          </div>
          <div style={{ flex: 1 }}>
            <Bar
              t={t}
              delay={1.15}
              value={2.4}
              max={MAX}
              label="LumaWall (GPU)"
              color="#35e07a"
              suffix="%"
              decimals={1}
            />
          </div>
        </div>

        {/* The scale, stated, so the two bars are read as one measurement rather than
            as two decorations. */}
        <div
          style={{
            marginTop: 40,
            display: 'flex',
            alignItems: 'center',
            gap: 20,
            opacity: foot,
          }}
        >
          <span style={{ fontFamily: FONT, fontSize: 18, color: '#8d939c' }}>{tx('1920×1080 · 60 fps · animasi 4K yang sama')}</span>
          <span style={{ width: 1, height: 18, background: 'rgba(255,255,255,.14)' }} />
          <span style={{ fontFamily: FONT, fontSize: 18, color: '#8d939c' }}>{tx('diukur di Windows 11, Ryzen 5')}</span>
        </div>
      </div>
    </div>
  );
}
