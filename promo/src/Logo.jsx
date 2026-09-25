// Logo — the real LumaWall app icon, animated.
//
// The old promo drew its own approximation of the logo, so it did not match the
// icon on the taskbar. This uses app-logo.png — the exact file the MSIX and the
// website ship — so the video cannot drift from the product.
//
// The entrance is a pure function of time.
//
// `minOpacity` exists for the opening frame. A promo whose first frame is black
// reads as a broken file: the viewer sees nothing, and a thumbnail generated from
// frame 1 is empty. The intro therefore starts the mark already substantially
// visible and animates its scale and glow, rather than fading it up from nothing.

import React from 'react';
import { seg, easeOut, easeOutBack } from './anim.js';

export default function Logo({
  t,
  size = 220,
  delay = 0,
  spin = false,
  glow = true,
  minOpacity = 0,
}) {
  const k = seg(t, delay, delay + 0.95);
  const e = easeOutBack(k, 0.9);
  const scale = 0.82 + 0.18 * e;
  const rotate = spin ? -9 * (1 - easeOut(k)) : 0;
  const opacity = minOpacity + (1 - minOpacity) * k;

  // The halo breathes on a slow loop so the mark never looks pasted on.
  const breathe = 1 + Math.sin(t * 1.15) * 0.045;

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      {glow && (
        <div
          style={{
            position: 'absolute',
            inset: -size * 0.35,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(226,69,74,.34) 0%, rgba(58,208,224,.14) 45%, transparent 70%)',
            filter: 'blur(26px)',
            opacity: Math.max(minOpacity, seg(t, delay, delay + 1.1)),
            transform: `scale(${breathe})`,
          }}
        />
      )}

      <img
        src="./logo/app-logo.png"
        alt="LumaWall"
        width={size}
        height={size}
        style={{
          position: 'relative',
          display: 'block',
          width: size,
          height: size,
          opacity,
          transform: `scale(${scale}) rotate(${rotate}deg)`,
        }}
      />
    </div>
  );
}
