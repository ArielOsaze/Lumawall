// Aurora — the drifting gradient backdrop, React Bits style.
//
// The old scenes used a fixed radial gradient, which made every frame look like a
// flat slide. Here two coloured blooms drift on independent long periods, so the
// backdrop is always moving slightly behind the content.
//
// Driven by absolute scene time, so the drift is reproducible.

import React from 'react';
import { loop } from './anim.js';

export default function Aurora({
  t,
  accent = '#e2454a',
  accent2 = '#3ad0e0',
  intensity = 0.28,
  drift = 1,
}) {
  // Two independent periods that do not share a common multiple, so the pattern
  // never visibly repeats within the length of the video.
  const a = loop(t, 18, 0);
  const b = loop(t, 22, 0.35);
  const ca = Math.cos(a * Math.PI * 2);
  const sa = Math.sin(a * Math.PI * 2);
  const cb = Math.cos(b * Math.PI * 2);
  const sb = Math.sin(b * Math.PI * 2);

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(120% 90% at 20% 0%, #1a0d12 0%, #0b0a0d 45%, #07070a 100%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          width: '70%',
          height: '70%',
          left: '-10%',
          top: '-15%',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accent} 0%, transparent 68%)`,
          filter: 'blur(70px)',
          opacity: intensity,
          transform: `translate(${ca * 62 * drift}px, ${sa * 54 * drift}px) scale(${1.06 + sa * 0.05})`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          width: '58%',
          height: '58%',
          right: '-8%',
          bottom: '-14%',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accent2} 0%, transparent 66%)`,
          filter: 'blur(80px)',
          opacity: intensity * 0.62,
          transform: `translate(${-cb * 54 * drift}px, ${-sb * 46 * drift}px) scale(${1.04 + cb * 0.045})`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,.028) 1px, transparent 1px),' +
            'linear-gradient(90deg, rgba(255,255,255,.028) 1px, transparent 1px)',
          backgroundSize: '68px 68px',
          maskImage: 'radial-gradient(120% 100% at 50% 40%, #000 35%, transparent 82%)',
          WebkitMaskImage: 'radial-gradient(120% 100% at 50% 40%, #000 35%, transparent 82%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(105% 78% at 50% 45%, transparent 42%, rgba(0,0,0,.72) 100%)',
        }}
      />
    </div>
  );
}
