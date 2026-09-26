// SceneBrowse — the app, filling the frame, being used.
//
// ── why this scene exists in this shape ─────────────────────────────────────
//
// The previous promo's catalogue scene put a screenshot in a frame beside a column of
// headline text, at 700px tall when the image is 579 - so 121px of the frame was
// empty and the scroll animation then pushed the top of the screenshot out of view.
// That is the "capture ke crop" note.
//
// It also wasted the screenshot: at that size the app's own text is unreadable, so
// the scene showed "an app" rather than "this app, which has these features".
//
// So the app is the SUBJECT here. It fills most of the frame at a size where its
// content can actually be read, the camera moves across it the way a product shot
// moves across a device, and the cursor works it - switching category, then picking a
// wallpaper. The type is small and set below, because the argument in this scene is
// made by the interface, not by a sentence.
//
// The screenshot is sized by WIDTH ONLY (see Kit.Shot), so it cannot be cropped.

import React from 'react';
import { Surface, Shot, Type, Eyebrow, Cursor, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

export default function SceneBrowse({ t, global }) {
  // The app arrives from below and settles.
  const enter = easeOutQuint(seg(t, 0.15, 1.25));

  // A slow lateral move across the screenshot, as if the camera were tracking along
  // it. Deliberately small: enough that the app is being looked at, not enough to
  // make its text swim.
  const pan = easeOut(seg(t, 0.9, 4.0));

  // The screenshot is 1580x836. At 1240 wide it is 656 tall, which leaves room for
  // the label above and the caption below inside a 1080 frame.
  const W = 1240;

  const caption = easeOut(seg(t, 1.8, 2.6));

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.05} warmSide="right" />

      {/* A soft pool of light behind the app, so it sits in the frame rather than on
          it. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(58% 52% at 50% 46%, rgba(255,255,255,.055) 0%, rgba(255,255,255,0) 70%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 96px',
        }}
      >
        <Eyebrow
          color="#3ad0e0"
          style={{
            marginBottom: 20,
            opacity: enter,
            transform: `translateY(${(1 - enter) * 14}px)`,
          }}
        >
          Katalog
        </Eyebrow>

        <div
          style={{
            opacity: enter,
            transform: `translateY(${(1 - enter) * 56}px) scale(${0.965 + 0.035 * enter})`,
          }}
        >
          {/* The screenshot is clipped by its own rounded frame, and the pan happens
              INSIDE that frame - so it can only ever reveal more of the screenshot,
              never cut it off. `Shot` has no height prop; adding one is how the
              previous version cropped two of its four screenshots. */}
          <Shot src="./shots/ui-discover.png" width={W} radius={16}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                // The pan: a small translation of the image inside the frame.
                transform: `translate3d(${-pan * 22}px, ${-pan * 10}px, 0) scale(${1 + 0.012 * pan})`,
              }}
            >
              <img
                src="./shots/ui-discover.png"
                alt=""
                style={{ display: 'block', width: '100%', height: 'auto' }}
              />
            </div>

            {/* The app is being used: the cursor travels to the category row and
                clicks, then moves down to a wallpaper. */}
            <Cursor
              t={t}
              from={[W * 0.42, 300]}
              to={[W * 0.30, 152]}
              start={0.5}
              dur={0.9}
              clickAt={1.45}
            />
            <Cursor
              t={t}
              from={[W * 0.30, 152]}
              to={[W * 0.52, 470]}
              start={2.1}
              dur={0.9}
              clickAt={3.05}
            />
          </Shot>
        </div>

        <div
          style={{
            marginTop: 26,
            display: 'flex',
            alignItems: 'baseline',
            gap: 22,
            opacity: caption,
            transform: `translateY(${(1 - caption) * 16}px)`,
          }}
        >
          <Type size={38} weight={800}>
            5.000+ wallpaper
          </Type>
          <span style={{ fontFamily: FONT, fontSize: 23, fontWeight: 500, color: '#9aa0a9' }}>
            cari, filter, unduh — semuanya di dalam aplikasi
          </span>
        </div>
      </div>
    </div>
  );
}
