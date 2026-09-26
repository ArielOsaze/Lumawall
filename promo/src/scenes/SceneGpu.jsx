// SceneGpu — where the work happens, and why that is the whole product.
//
// ── why this scene is drawn rather than screenshotted ───────────────────────
//
// This is the product's central claim: the animation is decoded and composited on the
// graphics chip, and the processor is left alone. There is no screenshot of that - it
// is an architecture - so the scene draws the pipeline and shows the load moving
// through it: frames travel the GPU path at full rate, and the CPU branch stays
// almost flat.
//
// The previous version made this claim with a sentence over a wallpaper, which is a
// claim. Drawing the path and animating the traffic through it is a demonstration.
//
// Nothing here is an image, so nothing here can be cropped.

import React from 'react';
import { Surface, Type, Eyebrow, Figure, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, easeOutExpo, loop } from '../anim.js';

// The frames that travel the GPU path. Each has its own phase so the path is
// continuously occupied rather than sending one frame and stopping.
const FRAMES = [0, 0.22, 0.44, 0.66, 0.88];

export default function SceneGpu({ t, global, variant = 0 }) {
  const head = easeOutQuint(seg(t, 0.1, 0.95));
  const body = easeOut(seg(t, 0.6, 1.4));

  // The path lights up, then traffic starts moving along it.
  const live = easeOut(seg(t, 0.9, 1.8));

  // The CPU figure settles low and stays there. It is the point of the scene, so it
  // is the largest number in it.
  const cpu = easeOutExpo(seg(t, 1.1, 2.5));
  const jitter = Math.sin(t * 7.1) * 0.28;

  const fps = easeOutExpo(seg(t, 1.3, 2.6));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.1} warmSide={variant ? 'left' : 'right'} grid={false} />

      {/* A cool wash, so the frame reads as the opposite of the previous scene's heat. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(68% 58% at 76% 30%, rgba(64,140,255,.16) 0%, rgba(64,140,255,0) 70%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 112px',
        }}
      >
        <div style={{ opacity: head, transform: `translateY(${(1 - head) * 20}px)` }}>
          <Eyebrow color="#4a9bff" style={{ marginBottom: 18 }}>
            Arsitektur
          </Eyebrow>
          <Type size={54}>
            Didekode di <span style={{ color: '#4a9bff' }}>GPU</span>, bukan di CPU.
          </Type>
        </div>

        {/* ── the pipeline ───────────────────────────────────────────────────── */}
        <div style={{ marginTop: 46, opacity: body }}>
          <div style={{ position: 'relative', height: 250 }}>
            {/* The two tracks. The upper one is the GPU path and carries the traffic;
                the lower one is the CPU path and stays empty. */}
            {[
              { y: 26, label: 'GPU', color: '#4a9bff', active: true, note: 'dekode · komposit · tampil' },
              { y: 158, label: 'CPU', color: '#6b7280', active: false, note: 'hampir tidak tersentuh' },
            ].map((track) => (
              <div key={track.label} style={{ position: 'absolute', left: 0, right: 0, top: track.y, height: 62 }}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 12,
                    border: `1px solid ${track.active ? 'rgba(74,155,255,.34)' : 'rgba(255,255,255,.08)'}`,
                    background: track.active ? 'rgba(74,155,255,.055)' : 'rgba(255,255,255,.018)',
                  }}
                />
                {/* The rail. */}
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    right: 0,
                    top: '50%',
                    height: 2,
                    background: track.active
                      ? 'linear-gradient(90deg, rgba(74,155,255,0), rgba(74,155,255,.5) 12%, rgba(74,155,255,.5) 88%, rgba(74,155,255,0))'
                      : 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.12) 12%, rgba(255,255,255,.12) 88%, rgba(255,255,255,0))',
                  }}
                />

                <div
                  style={{
                    position: 'absolute',
                    left: 22,
                    top: 0,
                    bottom: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONT,
                      fontSize: 20,
                      fontWeight: 800,
                      letterSpacing: '.1em',
                      color: track.active ? '#4a9bff' : '#6b7280',
                    }}
                  >
                    {track.label}
                  </span>
                  <span style={{ fontFamily: FONT, fontSize: 14, color: '#6b7280', marginTop: 3 }}>
                    {track.note}
                  </span>
                </div>

                {/* The traffic. Only the GPU track has it. */}
                {track.active &&
                  FRAMES.map((phase, i) => {
                    const p = ((t * 0.30 + phase) % 1);
                    // Fade at both ends so a frame appears to enter and leave the
                    // path rather than pop in and out of existence.
                    const o = Math.min(1, Math.min(p, 1 - p) * 5) * live;
                    return (
                      <div
                        key={i}
                        style={{
                          position: 'absolute',
                          left: `${8 + p * 84}%`,
                          top: '50%',
                          width: 46,
                          height: 30,
                          marginTop: -15,
                          borderRadius: 5,
                          border: '1px solid rgba(120,180,255,.55)',
                          background: 'linear-gradient(140deg, rgba(74,155,255,.42), rgba(74,155,255,.14))',
                          opacity: o,
                          boxShadow: '0 0 16px rgba(74,155,255,.32)',
                        }}
                      />
                    );
                  })}
              </div>
            ))}
          </div>
        </div>

        {/* ── the readings ──────────────────────────────────────────────────── */}
        <div style={{ marginTop: 40, display: 'flex', gap: 64, opacity: body }}>
          <div>
            <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, letterSpacing: '.16em', color: '#8d939c', marginBottom: 10 }}>
              PEMAKAIAN CPU
            </div>
            <Figure to={2.4 + jitter} t={cpu} dur={0.01} decimals={1} suffix="%" color="#35e07a" size={72} />
          </div>
          <div style={{ width: 1, background: 'rgba(255,255,255,.10)' }} />
          <div>
            <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, letterSpacing: '.16em', color: '#8d939c', marginBottom: 10 }}>
              FRAME RATE
            </div>
            <Figure to={60} t={fps} dur={1.2} suffix=" fps" color="#fff" size={72} />
          </div>
          <div style={{ width: 1, background: 'rgba(255,255,255,.10)' }} />
          <div>
            <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, letterSpacing: '.16em', color: '#8d939c', marginBottom: 10 }}>
              RESOLUSI
            </div>
            <Figure to={4} t={fps} dur={1.2} suffix="K" color="#fff" size={72} />
          </div>
        </div>
      </div>
    </div>
  );
}
