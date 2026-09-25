// SplitText — per-character reveal, React Bits style.
//
// The reveal is a pure function of time (see anim.js) rather than a library
// animation, so frame N always produces the same pixels.
//
// Why characters rather than lines: the old promo faded whole lines in, which
// reads as a slide transition. Revealing each character slightly after the last
// makes the line feel written.
//
// On gradient text: the natural approach - `background-clip: text` on the parent
// with transparent fill - does NOT work here, and the failure is silent. Each
// character is a transformed inline-block, which creates its own stacking
// context, so the parent's background never reaches the glyphs and the text
// renders fully transparent. The wordmark was invisible in the first render for
// exactly this reason.
//
// The fix is to paint the gradient on each character. That is only equivalent to
// a line-wide gradient when the gradient is purely vertical, which is why this
// component only accepts a top-to-bottom gradient. A horizontal one would restart
// on every letter and look banded.

import React from 'react';
import { seg, easeOut } from './anim.js';

export default function SplitText({
  text,
  t,
  delay = 0,
  stagger = 0.035,
  y = 42,
  blur = 10,
  opacityFloor = 0,  // characters never go below this, so a first frame is not blank
  gradient,          // e.g. 'linear-gradient(180deg,#fff 0%,#cfd2d8 62%,#9aa0aa 100%)'
  color = '#ffffff',
  style = {},
}) {
  const chars = Array.from(text);

  return (
    <span
      style={{ display: 'inline-block', whiteSpace: 'pre', ...style }}
      aria-label={text}
    >
      {chars.map((ch, i) => {
        const k = seg(t, delay + i * stagger, delay + i * stagger + 0.62);
        const e = easeOut(k);
        const op = opacityFloor + (1 - opacityFloor) * e;
        const gradientStyle = gradient
          ? {
              backgroundImage: gradient,
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              color: 'transparent',
            }
          : { color };

        return (
          <span
            key={i}
            aria-hidden="true"
            style={{
              display: 'inline-block',
              opacity: op,
              transform: `translateY(${(1 - e) * y}px)`,
              filter: blur ? `blur(${(1 - e) * blur}px)` : 'none',
              willChange: 'transform, opacity',
              ...gradientStyle,
            }}
          >
            {ch === ' ' ? '\u00A0' : ch}
          </span>
        );
      })}
    </span>
  );
}
