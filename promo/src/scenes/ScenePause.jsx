// ScenePause — the auto-pause feature, shown on a wallpaper that is playing.
//
// A window grows to cover the screen, the wallpaper underneath freezes and
// desaturates, a GPU meter drops to zero, then the window closes and the
// wallpaper resumes. The point of the feature — "it stops costing you anything
// when you are not looking at it" — is shown rather than asserted.

import React from 'react';
import Aurora from '../Aurora.jsx';
import SplitText from '../SplitText.jsx';
import WallpaperStage from '../WallpaperStage.jsx';
import { seg, easeOut, easeOutExpo, parallax } from '../anim.js';

const TOTAL = 52;
const FONT = '"Plus Jakarta Sans", sans-serif';

export default function ScenePause({ t, global }) {
  const head = parallax(global, TOTAL, 0.95, 26);
  const stage = parallax(global, TOTAL, 0.6, 34);

  // The window opens at 1.1s, covers by 1.75s, closes at 5.4s.
  const openK = easeOutExpo(seg(t, 1.1, 1.75));
  const closeK = easeOutExpo(seg(t, 5.4, 6.0));
  const cover = openK * (1 - closeK);
  const covered = cover > 0.985;

  const gpu = 21 - 21 * easeOut(seg(t, 1.85, 2.5)) + 21 * easeOut(seg(t, 5.6, 6.2));
  const gpuGood = gpu < 10.5;

  // The wallpaper holds one frame while covered, which is what "paused" looks
  // like: the same picture stays on screen instead of advancing.
  const stageT = covered ? 3.4 : global;

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* The monitor on the right is the subject. This is a second wallpaper far
          behind it so the beat is not floating on black. */}
      <div
        style={{
          position: 'absolute',
          inset: '-6%',
          opacity: 0.42,
          transform: `translate3d(${head.x * 0.5}px, ${head.y * 0.5}px, 0) scale(1.1)`,
        }}
      >
        <WallpaperStage clip="astra" t={global} offset={2.5} mode="fill" width="100%" radius={0} />
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(78% 68% at 50% 50%, rgba(7,7,10,.58) 0%, rgba(7,7,10,.78) 100%)',
        }}
      />
      <Aurora t={t} accent="#ff3b57" accent2="#3ad0e0" intensity={0.15} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 120px',
          gap: 68,
        }}
      >
        <div
          style={{
            width: 505,
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
            Pause otomatis
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 56,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-.035em',
              color: '#fff',
            }}
          >
            <SplitText text="Berhenti" t={t} delay={0.15} stagger={0.028} y={36} />
            <br />
            <SplitText text="saat tak terlihat." t={t} delay={0.85} stagger={0.032} y={36} />
          </div>
          <div
            style={{
              marginTop: 24,
              fontFamily: FONT,
              fontSize: 22,
              lineHeight: 1.55,
              color: '#a8aeb8',
              maxWidth: 460,
              opacity: seg(t, 1.5, 2.2),
              transform: `translateY(${(1 - easeOut(seg(t, 1.5, 2.2))) * 16}px)`,
            }}
          >
            Buka game fullscreen — wallpaper di layar itu berhenti, decode GPU turun ke
            nol. Tutup game, animasinya langsung jalan lagi.
          </div>
          <div
            style={{
              marginTop: 28,
              display: 'flex',
              alignItems: 'baseline',
              gap: 14,
              opacity: seg(t, 2.4, 2.9),
            }}
          >
            <span
              style={{
                fontFamily: FONT,
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: '.16em',
                color: '#7a838c',
                textTransform: 'uppercase',
              }}
            >
              Decode GPU
            </span>
            <span
              style={{
                fontFamily: FONT,
                fontSize: 42,
                fontWeight: 800,
                letterSpacing: '-.03em',
                color: gpuGood ? '#35e07a' : '#ff3b57',
                lineHeight: 1,
              }}
            >
              {Math.round(gpu)}%
            </span>
          </div>
        </div>

        <div
          style={{
            position: 'relative',
            flex: 1,
            // Sized from the wallpaper's own 16:9, so `object-fit: cover` in
            // WallpaperStage has nothing to crop.
            //
            // It was 640 tall while a 16:9 frame at this width is 623 - a 3% mismatch,
            // which cover resolves by trimming the sides. Small, but it is the same
            // class of mistake as the catalogue frame and it is free to avoid.
            height: 623,
            opacity: easeOut(seg(t, 0.4, 1.4)),
            transform: `translate3d(${stage.x + (1 - easeOut(seg(t, 0.4, 1.4))) * 50}px, ${stage.y}px, 0)
                        scale(${stage.scale})`,
          }}
        >
          <WallpaperStage
            clip="i14"
            t={stageT}
            offset={2}
            mode="fill"
            width="100%"
            radius={14}
            style={{
              position: 'absolute',
              inset: 0,
              border: '2px solid #24262c',
              boxShadow: '0 40px 80px -30px rgba(0,0,0,.9)',
              filter: covered ? 'saturate(.55) brightness(.7)' : 'none',
            }}
            overlay={
              <>
                {/* The fullscreen window that opens over the desktop.
                    It is a DARKENED view of the wallpaper, not a black rectangle.
                    Filling it with flat #0d0f13 made the right third of the frame an
                    empty dark box for the 3.6 seconds the window is up - a review of
                    the render called it "confusing, it just looks like a blank
                    screen", and it was right: the shot is about the wallpaper
                    FREEZING, so the wallpaper has to stay visible while it is frozen.
                    Dimming it says "behind the game" and still shows the product. */}
                <div
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    transform: 'translate(-50%,-50%)',
                    width: `${cover * 100}%`,
                    height: `${cover * 100}%`,
                    background: 'rgba(9,10,14,.42)',
                    backdropFilter: 'blur(3px) saturate(.7)',
                    border: '1px solid rgba(255,255,255,.07)',
                    borderRadius: cover > 0.99 ? 0 : 12,
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: cover > 0.01 ? 1 : 0,
                  }}
                >
                  {cover > 0.4 && (
                    <div
                      style={{
                        textAlign: 'center',
                        fontFamily: FONT,
                        opacity: Math.max(0, (cover - 0.55) / 0.45),
                      }}
                    >
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          letterSpacing: '.24em',
                          color: '#7a838c',
                          textTransform: 'uppercase',
                        }}
                      >
                        Aplikasi fullscreen
                      </div>
                      <div style={{ marginTop: 10, fontSize: 28, fontWeight: 700, color: '#e6e9ed' }}>
                        Wallpaper dijeda
                      </div>
                    </div>
                  )}
                </div>

                <div
                  style={{
                    position: 'absolute',
                    top: 18,
                    right: 18,
                    fontFamily: FONT,
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: '.18em',
                    color: '#35e07a',
                    border: '1px solid rgba(53,224,122,.4)',
                    background: 'rgba(53,224,122,.10)',
                    borderRadius: 999,
                    padding: '6px 14px',
                    textTransform: 'uppercase',
                    opacity: covered ? 1 : 0,
                    transform: `scale(${covered ? 1 : 0.9})`,
                  }}
                >
                  Dijeda
                </div>
              </>
            }
          />
        </div>
      </div>
    </div>
  );
}
