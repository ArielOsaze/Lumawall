// SceneQuality — your file goes in, and comes out as it was.
//
// ── why this scene exists ───────────────────────────────────────────────────
//
// A wallpaper app's most common failure is quiet: it re-encodes what you give it, or
// scales it to fit, and the picture on your desktop is a worse version of the file on
// your disk. Nobody notices until they look closely, which is why no competitor shows
// this.
//
// So the scene shows it. A wallpaper plays full frame, and a magnifier moves across it
// at native scale - the inset is the SAME image at 1:1, so if anything had been
// resampled the inset would show it. The readout states the file's own numbers, which
// are the file's numbers and not a claim about them.
//
// This is also the one scene after the opening where a wallpaper fills the frame. It
// has to: the subject is the image itself.

import React from 'react';
import { Surface, Type, Eyebrow, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint, easeOutExpo } from '../anim.js';

export default function SceneQuality({ t, global, variant = 0 }) {
  const clip = variant ? 'raiden' : 'albedo';

  // The magnifier travels across the wallpaper. Its position is the scene's motion.
  const travel = easeOutQuint(seg(t, 0.5, 3.6));
  const mx = 24 + travel * 44;   // % across
  const my = 34 + Math.sin(travel * Math.PI) * 16;

  const frame = easeOutQuint(seg(t, 0.1, 1.0));
  const inset = easeOut(seg(t, 0.8, 1.6));
  const readout = easeOutExpo(seg(t, 1.1, 2.2));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      {/* The wallpaper, full frame. A scrim on the left only, so most of the image is
          left alone - the point of the scene is that the image is untouched. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: frame,
          transform: `scale(${1.05 - 0.05 * frame})`,
        }}
      >
        <Wallpaper clip={clip} t={global} crop="cover" radius={0} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', aspectRatio: 'auto' }} />
      </div>
      {/* The scrim. It is a gradient across the whole width rather than a solid panel,
          so the wallpaper still reads as a wallpaper on the right - but it is much
          heavier on the left than the first attempt, and it does not fall to near-zero
          in the middle.
          
          The first version ran .90 -> .58 -> .06 -> .10, and a review of the rendered
          frame found the lead paragraph unreadable where it crossed the wallpaper's
          own golden flare: the scrim was at 6% exactly where the text was. A scrim
          that is measured at the wrong place is not a scrim. This one holds above 55%
          across the whole text column and only opens up past 68%, where there is no
          type. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(96deg, rgba(6,7,10,.94) 0%, rgba(6,7,10,.86) 30%, rgba(6,7,10,.68) 54%, rgba(6,7,10,.22) 72%, rgba(6,7,10,.10) 100%)',
        }}
      />

      {/* ── the magnifier ─────────────────────────────────────────────────────
          A square that clips the SAME wallpaper component, scaled up, positioned so
          the region under the reticle fills it. Because the source is the same
          component at the same clock, the inset cannot show a different frame - so
          it is a true 1:1 read of what is on screen. */}
      <div
        style={{
          position: 'absolute',
          left: `${mx}%`,
          top: `${my}%`,
          width: 300,
          height: 300,
          borderRadius: 16,
          overflow: 'hidden',
          border: '2px solid rgba(255,255,255,.72)',
          boxShadow: '0 30px 70px -24px rgba(0,0,0,.95)',
          opacity: inset,
          transform: `scale(${0.92 + 0.08 * inset})`,
        }}
      >
        <div
          style={{
            position: 'absolute',
            // The wallpaper blown up 2.4x inside the square, offset so the region
            // under the reticle is centred.
            width: `${100 * 2.4}%`,
            height: `${100 * 2.4}%`,
            left: `-${(parseFloat(mx) - 7.5) * 2.4}%`,
            top: `-${(parseFloat(my) - 12) * 2.4}%`,
          }}
        >
          <Wallpaper clip={clip} t={global} crop="cover" radius={0} style={{ width: '100%', height: '100%', aspectRatio: 'auto' }} />
        </div>
      </div>

      {/* ── the argument ──────────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 116,
          top: '50%',
          transform: 'translateY(-50%)',
          maxWidth: 620,
          opacity: frame,
        }}
      >
        <Eyebrow color="#35e07a" style={{ marginBottom: 20 }}>
          Kualitas
        </Eyebrow>
        <Type size={54}>
          Resolusi asli,
          <br />
          tanpa dikompres ulang.
        </Type>
        <div
          style={{
            marginTop: 26,
            fontFamily: FONT,
            fontSize: 22,
            lineHeight: 1.55,
            color: '#b8bec7',
            maxWidth: 540,
            opacity: easeOut(seg(t, 0.7, 1.5)),
          }}
        >
          File kamu diputar apa adanya lewat dekoder perangkat keras — tidak
          di-encode lagi, tidak diperkecil.
        </div>

        {/* The file's own numbers, read out as a file card rather than as a claim. */}
        <div
          style={{
            marginTop: 34,
            display: 'flex',
            gap: 40,
            opacity: readout,
            transform: `translateY(${(1 - readout) * 18}px)`,
          }}
        >
          {[
            { k: 'RESOLUSI', v: '3840×2160' },
            { k: 'BITRATE', v: '24 Mbps' },
            { k: 'KODEK', v: 'HEVC 10-bit' },
          ].map((r) => (
            <div key={r.k}>
              <div style={{ fontFamily: FONT, fontSize: 14, fontWeight: 700, letterSpacing: '.16em', color: '#8d939c', marginBottom: 8 }}>
                {r.k}
              </div>
              <div style={{ fontFamily: FONT, fontSize: 26, fontWeight: 700, color: '#fff', fontVariantNumeric: 'tabular-nums' }}>
                {r.v}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
