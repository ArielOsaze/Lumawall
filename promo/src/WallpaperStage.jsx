// WallpaperStage — a wallpaper that is genuinely playing, driven by the frame
// clock rather than by a <video> element.
//
// Why not a <video>: a video element plays from the wall clock. During a
// frame-by-frame render, the browser advances it independently of the renderer,
// so frame N would show a different picture on every run — and worse, the same
// frame could be captured twice or skipped. The output would not be reproducible
// and the wallpaper would visibly stutter.
//
// The clips are pre-extracted to image sequences (see tools/extract-clips.py).
// Picking `frames[floor(t * fps) % frames.length]` makes the wallpaper's position
// an exact function of the render time, so it plays smoothly and every render is
// identical.
//
// This matters because the product is a moving wallpaper. The earlier promo
// showed still screenshots of it, so the advert for a video wallpaper contained
// no video.

import React from 'react';

const CLIPS = {
  raiden: { dir: './frames/raiden', count: 60 },
  astra: { dir: './frames/astra', count: 60 },
  albedo: { dir: './frames/albedo', count: 60 },
  i14: { dir: './frames/i14', count: 60 },
};

const CLIP_FPS = 12;

function pad(n) {
  return String(n).padStart(3, '0');
}

export default function WallpaperStage({
  clip,
  t,
  offset = 0,
  mode = 'monitor',
  width = 520,
  radius = 10,
  style = {},
  overlay = null,
  children,
}) {
  const c = CLIPS[clip] || clip;
  const count = c.count;
  const index = Math.floor((t + offset) * CLIP_FPS) % count;

  const img = (
    <img
      src={`${c.dir}/f${pad(index)}.webp`}
      alt=""
      style={{ display: 'block', width: '100%', height: '100%', objectFit: 'cover' }}
    />
  );

  const frame = {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: radius,
    background: '#000',
    ...style,
  };

  if (mode === 'fill') {
    return (
      <div style={{ ...frame, width, height: '100%' }}>
        {img}
        {overlay}
        {children}
      </div>
    );
  }

  if (mode === 'card') {
    return (
      <div
        style={{
          ...frame,
          width,
          height: width * 0.5625,
          border: '1px solid rgba(255,255,255,.1)',
        }}
      >
        {img}
        {overlay}
        {children}
      </div>
    );
  }

  // A monitor: screen, then stand.
  return (
    <div style={{ position: 'relative', width }}>
      <div
        style={{
          ...frame,
          width,
          height: width * 0.5625,
          border: '2px solid #24262c',
          boxShadow: '0 30px 60px -24px rgba(0,0,0,.9)',
        }}
      >
        {img}
        {overlay}
        {children}
      </div>
      <div
        style={{
          width: width * 0.17,
          height: 15,
          margin: '0 auto',
          background: 'linear-gradient(180deg,#2a2d34,#191b20)',
          borderRadius: '0 0 5px 5px',
        }}
      />
      <div
        style={{
          width: width * 0.38,
          height: 8,
          margin: '0 auto',
          background: 'linear-gradient(180deg,#22242a,#15161a)',
          borderRadius: 5,
        }}
      />
    </div>
  );
}

export { CLIPS, CLIP_FPS };
