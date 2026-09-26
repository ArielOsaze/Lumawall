// ScenePause — pausing the wallpaper without closing it.
//
// ── what this scene argues, and why it is shaped this way ───────────────────
//
// The previous version showed this with a screenshot and a caption, which is a claim
// rather than a demonstration. The point of the feature is that the wallpaper STOPS
// while everything else carries on - so the scene has to show something that would be
// moving and then show it not moving.
//
// That is done by freezing the wallpaper's frame clock at the instant of the click
// and letting the rest of the frame continue: the status light keeps pulsing and the
// panel keeps drifting. The stillness of the wallpaper is the evidence, so nothing
// else in the frame is allowed to stop with it.
//
// The wallpaper sits inside a panel at its own aspect ratio. Nothing is cropped.

import React from 'react';
import { Surface, Shot, Type, Eyebrow, Cursor, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, loop } from '../anim.js';

export default function ScenePause({ t, global, variant = 0 }) {
  const CLICK = 1.5;

  const head = easeOutQuint(seg(t, 0.1, 0.95));
  const panel = easeOutQuint(seg(t, 0.3, 1.2));

  // The wallpaper's clock stops dead at the click. Everything else keeps running.
  const clicked = t >= CLICK;
  const frozenAt = CLICK;

  const statusK = easeOut(seg(t, CLICK + 0.15, CLICK + 0.7));
  const idle = loop(t, 30, 0);

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={0.95} warmSide={variant ? 'right' : 'left'} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 70,
          padding: '0 108px',
        }}
      >
        {/* ── the argument ───────────────────────────────────────────────────── */}
        <div style={{ width: 600, flexShrink: 0 }}>
          <Eyebrow color="#ffb020" style={{ marginBottom: 20, opacity: head }}>
            Pause
          </Eyebrow>
          <Type size={54} style={{ opacity: head, transform: `translateY(${(1 - head) * 22}px)` }}>
            Berhenti tanpa
            <br />
            menutup apa pun.
          </Type>
          <div
            style={{
              marginTop: 26,
              fontFamily: FONT,
              fontSize: 22,
              lineHeight: 1.55,
              color: '#a8aeb8',
              maxWidth: 540,
              opacity: easeOut(seg(t, 0.65, 1.35)),
            }}
          >
            Wallpaper yang berat tidak perlu dihapus — cukup dijeda saat kamu butuh
            tenaganya.
          </div>

          <div
            style={{
              marginTop: 34,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              opacity: statusK,
              transform: `translateY(${(1 - statusK) * 14}px)`,
            }}
          >
            <span
              style={{
                width: 11,
                height: 11,
                borderRadius: '50%',
                background: '#ffb020',
                boxShadow: `0 0 0 ${4 + 3 * Math.sin(t * 5)}px rgba(255,176,32,.16)`,
              }}
            />
            <span style={{ fontFamily: FONT, fontSize: 21, fontWeight: 600, color: '#e6e9ee' }}>
              Wallpaper dijeda — aplikasi tetap jalan
            </span>
          </div>
        </div>

        {/* ── the app, with the wallpaper inside it ─────────────────────────── */}
        <div
          style={{
            flex: 1,
            opacity: panel,
            transform: `translateY(${(1 - panel) * 34}px) translateX(${idle * 6}px)`,
          }}
        >
          <Shot src="./shots/ui-performance.png" width={880} radius={15}>
            <div
              style={{
                position: 'absolute',
                left: '8.5%',
                right: '8.5%',
                top: '15%',
                borderRadius: 10,
                overflow: 'hidden',
                border: '1px solid rgba(255,255,255,.12)',
              }}
            >
              <Wallpaper clip={variant ? 'albedo' : 'i14'} t={clicked ? frozenAt : t} width="100%" radius={0} />
              <div
                style={{
                  position: 'absolute',
                  left: 12,
                  top: 12,
                  fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                  fontSize: 14,
                  fontWeight: 600,
                  letterSpacing: '.06em',
                  color: clicked ? '#ffb020' : '#35e07a',
                  background: 'rgba(0,0,0,.66)',
                  border: `1px solid ${clicked ? 'rgba(255,176,32,.42)' : 'rgba(53,224,122,.42)'}`,
                  borderRadius: 6,
                  padding: '5px 11px',
                }}
              >
                {clicked ? 'PAUSED' : 'PLAYING'}
              </div>
            </div>

            <Cursor
              t={t}
              from={[880 * 0.66, 500]}
              to={[880 * 0.80, 236]}
              start={0.4}
              dur={0.9}
              clickAt={CLICK}
            />
          </Shot>
        </div>
      </div>
    </div>
  );
}
