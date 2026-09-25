// ShinyText — a light sweep that travels across the letters, React Bits style.
//
// Used for the small uppercase taglines. The sweep is a pure function of time, so
// it is reproducible; it is implemented as a moving gradient clipped to the glyphs.
//
// Note on the clip: the gradient is applied per character for the same reason
// described in SplitText - a transformed inline-block does not inherit a
// background-clip from its parent. Here the characters are not individually
// animated, so the whole word can be a single element and the sweep stays
// continuous across it.

import React from 'react';
import { loop } from './anim.js';

export default function ShinyText({
  text,
  t,
  baseColor = '#e2454a',
  shineColor = '#ffffff',
  speed = 3.2,
  spread = 22,
  style = {},
}) {
  const p = loop(t, speed) * (100 + spread * 2) - spread;

  return (
    <span
      style={{
        display: 'inline-block',
        backgroundImage: `linear-gradient(100deg, ${baseColor} ${p - spread}%, ${shineColor} ${p}%, ${baseColor} ${p + spread}%)`,
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        color: 'transparent',
        ...style,
      }}
    >
      {text}
    </span>
  );
}
