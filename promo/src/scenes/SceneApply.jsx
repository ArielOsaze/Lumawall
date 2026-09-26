// SceneApply — picking a wallpaper and watching it land on the desktop.
//
// ── the scene the promo was missing ─────────────────────────────────────────
//
// The previous version never showed the product's actual loop: you choose something,
// you apply it, and the desktop changes. It showed screenshots of the app and
// screenshots of a desktop, but never the CAUSE and the EFFECT in one shot.
//
// That is the moment a viewer decides whether the product does something they want,
// and it costs nothing to show: the app panel on the left, the wallpaper it is about
// to apply on the right, and the click that connects them. The frame after the click
// is the wallpaper full-bleed, which is what applying it means.
//
// This is also where a wallpaper is allowed to fill the frame - it is the payoff of
// the scene, not the backdrop of it.

import React from 'react';
import { Surface, Shot, Type, Eyebrow, Cursor, WallpaperFull, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, easeOutExpo } from '../anim.js';

export default function SceneApply({ t, global, variant = 0 }) {
  const clip = variant ? 'i14' : 'astra';
  const label = variant ? 'I-14 Thousand-Faced' : 'Astra Yao';

  // The app panel slides in from the left and holds. The wallpaper on the right is
  // already playing, so the scene is in motion before the click.
  const panel = easeOutQuint(seg(t, 0.1, 1.0));
  const wp = easeOutQuint(seg(t, 0.25, 1.15));

  // The click at 1.6s, then the wallpaper takes the frame.
  const CLICK = 1.6;
  const take = easeOutExpo(seg(t, CLICK + 0.1, CLICK + 1.0));

  // A confirmation that reads as a UI event rather than as a caption.
  const done = easeOut(seg(t, CLICK + 0.35, CLICK + 1.0));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={0.9} warmSide="left" />

      {/* ── the wallpaper, taking the frame after the click ─────────────────── */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: take,
          transform: `scale(${1.06 - 0.06 * take})`,
        }}
      >
        <WallpaperFull clip={clip} t={global} offset={2} scrim={0.42} />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(100deg, rgba(6,7,10,.86) 0%, rgba(6,7,10,.52) 40%, rgba(6,7,10,.16) 100%)',
          }}
        />
      </div>

      {/* ── the app panel, before and after ─────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 60,
          padding: '0 108px',
          // The whole composition pulls back a little as the wallpaper takes over,
          // so the transition reads as the camera reacting rather than as a wipe.
          transform: `scale(${1 - 0.05 * take}) translateX(${-take * 60}px)`,
          opacity: 1 - 0.55 * take,
        }}
      >
        <div style={{ width: 660, flexShrink: 0 }}>
          <Eyebrow style={{ marginBottom: 20, opacity: panel }}>Terapkan</Eyebrow>
          <Type size={54} style={{ opacity: panel, transform: `translateY(${(1 - panel) * 24}px)` }}>
            Pilih, klik,
            <br />
            langsung ganti.
          </Type>
          <div
            style={{
              marginTop: 24,
              fontFamily: FONT,
              fontSize: 22,
              lineHeight: 1.5,
              color: '#a8aeb8',
              maxWidth: 560,
              opacity: easeOut(seg(t, 0.7, 1.4)),
            }}
          >
            Tanpa keluar dari aplikasi, tanpa atur file manual.
          </div>

          <div
            style={{
              marginTop: 32,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              opacity: done,
            }}
          >
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: '50%',
                background: '#35e07a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path d="M5 13l4 4L19 7" fill="none" stroke="#07220f" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span style={{ fontFamily: FONT, fontSize: 21, fontWeight: 600, color: '#e6e9ee' }}>
              Diterapkan ke Display 1
            </span>
          </div>
        </div>

        {/* The app's own library panel, at its real aspect ratio - the wallpaper it
            is about to apply sits inside it, playing. */}
        <div style={{ flex: 1, opacity: wp, transform: `translateY(${(1 - wp) * 34}px)` }}>
          <Shot src="./shots/ui-library.png" width={880} radius={15}>
            <Cursor t={t} from={[880 * 0.74, 460]} to={[880 * 0.52, 300]} start={0.35} dur={0.85} clickAt={CLICK} />
          </Shot>
        </div>
      </div>

      {/* The wallpaper's own name, once it has taken the frame. */}
      <div
        style={{
          position: 'absolute',
          left: 108,
          bottom: 92,
          opacity: take * easeOut(seg(t, CLICK + 0.6, CLICK + 1.2)),
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 15,
            fontWeight: 700,
            letterSpacing: '.18em',
            textTransform: 'uppercase',
            color: '#ff6b7f',
            marginBottom: 12,
          }}
        >
          Sedang dipakai
        </div>
        <div style={{ fontFamily: FONT, fontSize: 44, fontWeight: 800, letterSpacing: '-.03em', color: '#fff' }}>
          {label}
        </div>
      </div>
    </div>
  );
}
