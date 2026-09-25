// MotionFilters — the SVG filters that make a handover read as a camera whip.
//
// ── why this exists ─────────────────────────────────────────────────────────
//
// Three attempts at the handover failed, and the reason is worth writing down:
//
//   1. Crossfade — both beats semi-visible in the same place. Reads as a glitch.
//   2. Slide — no overlap, but 1920px over 1.6s with no blur. That is literally
//      PowerPoint's "Push", which is what the review called it.
//   3. Slide with `filter: blur()` — the blur was correct in *amount* (matched the
//      per-frame movement) but wrong in *direction*. CSS blur() is isotropic: it
//      blurs in every direction at once, so instead of a smear along the axis of
//      travel you get a uniformly muddy frame with no readable content. The
//      review described the middle frames as "a muddy blackout", which is exactly
//      what an isotropic blur of a dark scene looks like.
//
// A real whip pan smears ALONG the direction of travel and not across it. That is
// what SVG's feGaussianBlur gives: `stdDeviation` takes two values, x and y, so a
// horizontal whip can be blurred 120px horizontally and 0px vertically. The
// result is directional streaks rather than fog.
//
// These filters live in one <svg> at the top of the frame. Referencing them costs
// one attribute per scene.

import React from 'react';

// How much blur, in pixels, along the axis of travel, at the peak of a handover.
//
// The value is set so the smear spans roughly one frame's worth of movement: at
// 30fps over a 0.22s handover there are ~7 frames, so the content moves about
// 150px between captures. A blur near that covers the gap; much more and the
// content dissolves.
export const WHIP_BLUR = 150;

// The zoom handovers blur radially, which feGaussianBlur cannot do. They use an
// isotropic blur at a lower strength instead, plus scale — the scale is what
// carries the motion, and the blur only softens it.
export const ZOOM_BLUR = 34;

export default function MotionFilters() {
  return (
    <svg
      width="0"
      height="0"
      style={{ position: 'absolute', pointerEvents: 'none' }}
      aria-hidden="true"
    >
      <defs>
        {/* Horizontal whip: blurred along x, sharp along y. */}
        <filter id="whip-x" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation={`${WHIP_BLUR} 0`} />
        </filter>

        {/* Vertical whip: blurred along y, sharp along x. The vertical travel is
            620px against the horizontal 1080px, so the blur scales with it — at
            0.6 of the horizontal value it smeared proportionally further than the
            content moved and dissolved the frame. */}
        <filter id="whip-y" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation={`0 ${WHIP_BLUR * 0.35}`} />
        </filter>

        {/* Zoom: no direction, so a modest isotropic blur. The scale does the work. */}
        <filter id="zoom" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation={ZOOM_BLUR} />
        </filter>
      </defs>
    </svg>
  );
}
