// SceneMulti — three monitors, three wallpapers, configured in the app.
//
// ── the shape this replaces ─────────────────────────────────────────────────
//
// The previous version showed this as three wallpapers side by side on a wallpaper
// background - which is a picture of wallpapers, not of the feature. The feature is
// that each SCREEN is configured independently, and the evidence for that is the
// app's own displays panel with three entries in it.
//
// So the panel is the subject, the three screens are the illustration, and the link
// between them is drawn: each screen lights up in turn, in that screen's own accent
// colour, and its caption arrives with it. That sequence is the argument, and it is
// the one thing a static screenshot cannot show.
//
// The wallpapers appear at their own aspect ratio inside monitor frames - no crop,
// because a monitor bezel is not a reason to cut an image.

import React from 'react';
import { Surface, Type, Eyebrow, Shot, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

const SCREENS = [
  { clip: 'i14', label: 'Display 1', color: '#ff3b57' },
  { clip: 'albedo', label: 'Display 2', color: '#3ad0e0' },
  { clip: 'raiden', label: 'Display 3', color: '#35e07a' },
];

export default function SceneMulti({ t, global, variant = 0 }) {
  const head = easeOutQuint(seg(t, 0.1, 1.0));
  const panel = easeOutQuint(seg(t, 0.35, 1.35));

  // Each screen lights up in turn, and its caption draws with it. That sequence is
  // the scene's motion: three arrivals, not one.
  const arrivals = SCREENS.map((_, i) => easeOutQuint(seg(t, 1.5 + i * 0.55, 2.3 + i * 0.55)));

  // After all three, the whole row drifts, so the shot never settles into a still.
  const drift = easeOut(seg(t, 3.4, 5.0)) * -22;

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.0} warmSide={variant ? 'left' : 'right'} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 104px',
          gap: 34,
        }}
      >
        <div style={{ opacity: head, transform: `translateY(${(1 - head) * 18}px)` }}>
          <Eyebrow color="#3ad0e0" style={{ marginBottom: 16 }}>
            Multi-monitor
          </Eyebrow>
          <Type size={52}>Tiap layar, pengaturannya sendiri.</Type>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 54,
            transform: `translateX(${drift}px)`,
          }}
        >
          {/* ── the app's displays panel ─────────────────────────────────────── */}
          <div
            style={{
              width: 560,
              flexShrink: 0,
              opacity: panel,
              transform: `translateY(${(1 - panel) * 30}px)`,
            }}
          >
            <Shot src="./shots/ui-displays.png" width={560} radius={14} />
          </div>

          {/* ── the three screens ───────────────────────────────────────────── */}
          <div style={{ flex: 1, display: 'flex', gap: 26, alignItems: 'flex-start' }}>
            {SCREENS.map((s, i) => {
              const k = arrivals[i];
              return (
                <div
                  key={s.label}
                  style={{
                    flex: 1,
                    opacity: 0.32 + 0.68 * k,
                    transform: `translateY(${(1 - k) * 30}px) scale(${0.94 + 0.06 * k})`,
                  }}
                >
                  {/* The monitor: a bezel around the wallpaper at its own ratio. */}
                  <div
                    style={{
                      position: 'relative',
                      borderRadius: 12,
                      padding: 7,
                      background: 'linear-gradient(180deg,#26282f,#15161a)',
                      boxShadow: `0 26px 60px -26px rgba(0,0,0,.9), 0 0 0 ${k > 0.5 ? 1 : 0}px ${s.color}55`,
                    }}
                  >
                    <Wallpaper clip={s.clip} t={global} width="100%" radius={7} />
                  </div>
                  {/* The stand. */}
                  <div style={{ width: '18%', height: 12, margin: '0 auto', background: 'linear-gradient(180deg,#2a2d34,#191b20)', borderRadius: '0 0 5px 5px' }} />
                  <div style={{ width: '40%', height: 7, margin: '0 auto', background: 'linear-gradient(180deg,#22242a,#15161a)', borderRadius: 5 }} />

                  <div
                    style={{
                      marginTop: 14,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                      opacity: k,
                    }}
                  >
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
                    <span style={{ fontFamily: FONT, fontSize: 17, fontWeight: 600, color: '#c3c8d0' }}>
                      {s.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
