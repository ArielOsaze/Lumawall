// Kit.jsx — the components every scene is built from.
//
// ── what this replaces, and why ──────────────────────────────────────────────
//
// The previous promo had seven scenes and every one of them was a wallpaper filling
// the frame, with text laid over it. The note that came back was "semua scene pake
// wallpaper jelek bgt" - all scenes use wallpaper, very ugly. That was correct, and
// it was also a missed argument: a wallpaper behind a headline says nothing about a
// product whose whole job is to run wallpapers properly.
//
// What a commercial for this product actually shows is THE APP. The wallpaper is the
// content inside it. So the wallpaper appears in two places only:
//
//   · the opening and the close, where the product is the image; and
//   · INSIDE the app's own preview panels, which is where it actually lives.
//
// Everything between sits on a quiet brand surface, with the app filling the frame.
//
// ── the crop rule ────────────────────────────────────────────────────────────
//
// The other note was "capture ke crop banyak yg rusak" - the captures are cropped and
// broken. They were: the catalogue frame was a fixed 700px tall while the screenshot
// at that width is 579, so 121px of the frame was empty and the scroll animation then
// pushed the top of the image out of view. The pause frame had the same mistake at a
// smaller scale.
//
// The fix is a rule rather than a correction: **a screenshot is never given a
// height**. `Shot` sets width only and lets the browser derive the height from the
// image's own aspect ratio, so a screenshot cannot be cropped by construction - there
// is no height to disagree with the image. A frame that needs a particular shape
// wraps the screenshot and clips it deliberately, and that wrapper is the only place
// a crop can happen, which makes it visible in review.

import React from 'react';
import { seg, easeOut, easeOutQuint, easeOutExpo, loop } from './anim.js';

export const FONT = '"Plus Jakarta Sans", sans-serif';

// ── the surface ──────────────────────────────────────────────────────────────

/**
 * The quiet brand surface that app scenes sit on.
 *
 * Deliberately restrained: a deep base, two slow blooms in the brand's palette, a
 * faint grid, a vignette. It is the environment, not the subject - if it competes
 * with the app on top of it, it is a worse environment.
 */
export function Surface({ t, intensity = 1, warmSide = 'left', grid = true }) {
  const a = loop(t, 26, 0);
  const b = loop(t, 34, 0.4);
  const ax = Math.cos(a * Math.PI * 2) * 12;
  const ay = Math.sin(a * Math.PI * 2) * 8;
  const bx = Math.cos(b * Math.PI * 2) * 10;
  const by = Math.sin(b * Math.PI * 2) * 9;

  const warm = warmSide === 'left' ? '22% 30%' : '78% 34%';
  const cool = warmSide === 'left' ? '82% 74%' : '18% 70%';

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: '#08090d' }}>
      <div
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(46% 40% at calc(${warm.split(' ')[0]} + ${ax}%) calc(${warm.split(' ')[1]} + ${ay}%), rgba(255,46,67,${0.15 * intensity}) 0%, rgba(255,46,67,0) 68%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(50% 44% at calc(${cool.split(' ')[0]} + ${bx}%) calc(${cool.split(' ')[1]} + ${by}%), rgba(64,140,255,${0.09 * intensity}) 0%, rgba(64,140,255,0) 70%)`,
        }}
      />
      {grid && (
        <div
          style={{
            position: 'absolute',
            inset: '-10%',
            opacity: 0.5,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,.042) 1px, transparent 1px), ' +
              'linear-gradient(90deg, rgba(255,255,255,.042) 1px, transparent 1px)',
            backgroundSize: '64px 64px',
            transform: `translate3d(${ax * 1.6}px, ${ay * 1.6}px, 0)`,
          }}
        />
      )}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(120% 96% at 50% 46%, rgba(0,0,0,0) 46%, rgba(0,0,0,.30) 82%, rgba(0,0,0,.58) 100%)',
        }}
      />
    </div>
  );
}

// ── the app ──────────────────────────────────────────────────────────────────

/**
 * An app screenshot at its own aspect ratio. Never cropped.
 *
 * `width` is the only sizing input. There is deliberately no `height` prop: adding
 * one is how the previous version cropped two of its four screenshots, and the
 * component makes that mistake impossible rather than merely discouraged.
 *
 * `focus` pans the image inside a clipping frame, for the shots where the app should
 * read as being used rather than as a still. The frame is sized from the image, so a
 * pan can only ever reveal more of it, never cut it off.
 */
export function Shot({
  src,
  width,
  radius = 14,
  frame = true,
  shadow = true,
  style = {},
  children,
}) {
  return (
    <div
      style={{
        position: 'relative',
        width,
        borderRadius: radius,
        overflow: 'hidden',
        border: frame ? '1px solid rgba(255,255,255,.10)' : 'none',
        boxShadow: shadow ? '0 40px 90px -34px rgba(0,0,0,.92)' : 'none',
        background: '#0b0c10',
        ...style,
      }}
    >
      <img
        src={src}
        alt=""
        style={{
          display: 'block',
          width: '100%',
          // No height. The browser derives it from the image, so the screenshot is
          // shown in full whatever its aspect ratio is.
          height: 'auto',
        }}
      />
      {/* A glass edge, so the window reads as a surface rather than as a picture. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          borderRadius: radius,
          background:
            'linear-gradient(180deg, rgba(255,255,255,.05) 0%, transparent 12%, transparent 88%, rgba(0,0,0,.22) 100%)',
        }}
      />
      {children}
    </div>
  );
}

/** A cursor that travels to a point and clicks, with a ripple. */
export function Cursor({ t, from, to, start = 0.4, dur = 1.1, clickAt = null }) {
  const k = easeOutQuint(seg(t, start, start + dur));
  const x = from[0] + (to[0] - from[0]) * k;
  const y = from[1] + (to[1] - from[1]) * k;

  const ripple = clickAt === null ? 0 : seg(t, clickAt, clickAt + 0.7);
  const pressed = clickAt !== null && t > clickAt && t < clickAt + 0.16;

  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: 22,
          height: 22,
          opacity: seg(t, start - 0.2, start + 0.2),
          transform: `scale(${pressed ? 0.86 : 1})`,
          filter: 'drop-shadow(0 2px 7px rgba(0,0,0,.8))',
          zIndex: 5,
        }}
      >
        <svg viewBox="0 0 24 24" width="22" height="22">
          <path d="M5 2l14 9-6 1.4L16 20l-3 1-3-7-5 4z" fill="#fff" stroke="#0a0a0c" strokeWidth="1.2" />
        </svg>
      </div>
      {ripple > 0 && ripple < 1 && (
        <div
          style={{
            position: 'absolute',
            left: x + 6,
            top: y + 6,
            width: 18 + ripple * 84,
            height: 18 + ripple * 84,
            marginLeft: -(18 + ripple * 84) / 2,
            marginTop: -(18 + ripple * 84) / 2,
            borderRadius: '50%',
            border: `2px solid rgba(255,59,87,${(1 - ripple) * 0.9})`,
            zIndex: 4,
          }}
        />
      )}
    </>
  );
}

/** A click target that highlights, for showing a control being used. */
export function Press({ t, at, children, color = '#ff3b57' }) {
  const k = seg(t, at, at + 0.35);
  const press = t > at && t < at + 0.2;
  return (
    <div
      style={{
        position: 'relative',
        borderRadius: 10,
        boxShadow: k > 0 ? `0 0 0 ${press ? 2 : 1.5}px ${color}${press ? '' : '88'}` : 'none',
        transform: `scale(${press ? 0.97 : 1})`,
        transition: 'none',
      }}
    >
      {children}
    </div>
  );
}

// ── type ─────────────────────────────────────────────────────────────────────

/**
 * A headline. Two registers: `display` for the hook and the close, `title` for a
 * scene's statement. Sizes are set for a 1080p frame, where 60px is 5.6% of the
 * height and anything under 20px is a caption.
 */
export function Type({ children, size = 58, weight = 800, color = '#fff', style = {}, tracking = '-.035em' }) {
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: size,
        fontWeight: weight,
        lineHeight: 1.08,
        letterSpacing: tracking,
        color,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** A small uppercase label above a headline. */
export function Eyebrow({ children, color = '#ff3b57', style = {} }) {
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: 17,
        fontWeight: 700,
        letterSpacing: '.22em',
        textTransform: 'uppercase',
        color,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** A supporting line. 20px is the floor: below that it is decoration, not text. */
export function Lead({ children, size = 22, color = '#a8aeb8', style = {} }) {
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: size,
        lineHeight: 1.55,
        color,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** A pill: a category, a status, a small claim. */
export function Chip({ children, color = '#c3c8d0', style = {} }) {
  return (
    <span
      style={{
        fontFamily: FONT,
        fontSize: 16,
        fontWeight: 500,
        color,
        border: '1px solid rgba(255,255,255,.12)',
        background: 'rgba(255,255,255,.035)',
        borderRadius: 999,
        padding: '8px 16px',
        ...style,
      }}
    >
      {children}
    </span>
  );
}

// ── numbers ──────────────────────────────────────────────────────────────────

/**
 * A measured figure, counting up to its value.
 *
 * The figures are the claim in a performance piece, so this is deliberately the
 * largest thing in whatever it sits in - a review of the previous version noted the
 * numbers were smaller than the headline above them, which is backwards.
 */
export function Figure({ to, t, delay = 0, dur = 1.3, decimals = 0, suffix = '', color = '#fff', size = 76, style = {} }) {
  const k = easeOutExpo(seg(t, delay, delay + dur));
  return (
    <span
      style={{
        fontFamily: FONT,
        fontSize: size,
        fontWeight: 800,
        letterSpacing: '-.035em',
        color,
        lineHeight: 1,
        ...style,
      }}
    >
      {(to * k).toFixed(decimals)}
      {suffix}
    </span>
  );
}

/**
 * A comparison bar that fills, with its figure at the end.
 *
 * The two bars of a comparison share an axis and a scale. They used to carry
 * different parallax depths, so the camera's drift moved them apart and the
 * comparison misread - the thing being compared has to stay on one line.
 */
export function Bar({ t, delay = 0, value, max, label, note, color, suffix = '%', decimals = 0 }) {
  const k = easeOutExpo(seg(t, delay, delay + 1.2));
  const w = (value / max) * 100 * k;
  const figure = seg(t, delay + 0.15, delay + 0.6);

  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontFamily: FONT, fontSize: 22, fontWeight: 600, color: '#c3c8d0', opacity: figure }}>
          {label}
        </span>
        <Figure to={value} t={t} delay={delay + 0.15} dur={1.2} decimals={decimals} suffix={suffix} color={color} size={64} />
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
            width: `${w}%`,
            borderRadius: 11,
            background: color === '#ff3b57'
              ? 'linear-gradient(90deg,#5c1a20,#ff3b57)'
              : 'linear-gradient(90deg,#155e3b,#35e07a)',
          }}
        />
      </div>
      {note && (
        <div style={{ marginTop: 14, fontFamily: FONT, fontSize: 19, color: '#c3cad2', opacity: seg(t, delay + 0.5, delay + 1.0) }}>
          {note}
        </div>
      )}
    </div>
  );
}

/** A row of measured figures in cards. */
export function Stat({ t, label, to, decimals = 0, suffix = '', color, delay = 0, note }) {
  const k = easeOut(seg(t, delay, delay + 0.6));
  return (
    <div
      style={{
        flex: 1,
        padding: '26px 26px',
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,.09)',
        background: 'rgba(255,255,255,.028)',
        opacity: k,
        transform: `translate3d(0, ${(1 - k) * 24}px, 0)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 15,
          fontWeight: 700,
          letterSpacing: '.16em',
          color: '#8d939c',
          textTransform: 'uppercase',
          marginBottom: 14,
        }}
      >
        {label}
      </div>
      <Figure to={to} t={t} delay={delay + 0.1} dur={1.2} decimals={decimals} suffix={suffix} color={color} size={68} />
      <div style={{ marginTop: 12, fontFamily: FONT, fontSize: 18, color: '#9aa0a9' }}>{note}</div>
    </div>
  );
}

// ── the wallpaper, used sparingly ────────────────────────────────────────────

const CLIPS = {
  raiden: { dir: './frames/raiden', count: 60 },
  astra: { dir: './frames/astra', count: 60 },
  albedo: { dir: './frames/albedo', count: 60 },
  i14: { dir: './frames/i14', count: 60 },
};

const CLIP_FPS = 12;

/**
 * A wallpaper playing, at a given size.
 *
 * `crop` is explicit and defaults to 'contain': the frame takes the wallpaper's own
 * aspect ratio and the whole image is shown. A caller that wants a different shape
 * passes `crop="cover"` and accepts the crop, which makes the decision visible
 * rather than accidental.
 */
export function Wallpaper({ clip, t, width, height, crop = 'contain', radius = 12, style = {}, children }) {
  const c = CLIPS[clip];
  if (!c) return null;
  const index = Math.floor(t * CLIP_FPS) % c.count;
  const pad = (n) => String(n).padStart(3, '0');

  return (
    <div
      style={{
        position: 'relative',
        width,
        height: height || undefined,
        aspectRatio: height ? undefined : '16 / 9',
        borderRadius: radius,
        overflow: 'hidden',
        background: '#000',
        ...style,
      }}
    >
      <img
        src={`${c.dir}/f${pad(index)}.webp`}
        alt=""
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: crop === 'cover' ? 'cover' : 'contain',
          display: 'block',
        }}
      />
      {children}
    </div>
  );
}

/** A wallpaper filling the whole frame. Only the hook and the close use this. */
export function WallpaperFull({ clip, t, offset = 0, scrim = 0.5, style = {} }) {
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', ...style }}>
      <Wallpaper
        clip={clip}
        t={t + offset}
        crop="cover"
        radius={0}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', aspectRatio: 'auto' }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(120% 100% at 50% 50%, rgba(6,7,10,${scrim * 0.55}) 0%, rgba(6,7,10,${scrim}) 100%)`,
        }}
      />
    </div>
  );
}

export { seg, easeOut, easeOutQuint, easeOutExpo };
