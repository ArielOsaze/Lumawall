// MotionFilters — one directional blur, sized by the caller from real motion.
//
// ── why directional, and why the amount is a prop ───────────────────────────
//
// Three attempts at the transition failed, and the reasons are worth keeping:
//
//   1. Crossfade — both shots semi-visible in the same place. Reads as a glitch.
//   2. Slide — no overlap, but 1920px over 1.6s with no blur. That is literally
//      PowerPoint's "Push".
//   3. Slide with `filter: blur()` — right in amount, wrong in direction. CSS
//      blur() is isotropic: it blurs in every direction at once, so instead of a
//      smear along the axis of travel you get a uniformly muddy frame with no
//      readable content.
//
// A camera smears ALONG its direction of travel. That is what feGaussianBlur
// gives: `stdDeviation` takes two values, x and y, so a fast diagonal move can be
// blurred along the diagonal and left sharp across it.
//
// The amount is a prop, never a constant. A fixed value was the fourth failure:
// the blur has to follow how far the content actually moves between two captured
// frames, so it is computed by the caller from the camera's speed and passed in.

import React from 'react';

// A hard ceiling. Past this the frame dissolves rather than smears, and a shot that
// cannot be read is worse than a hard cut.
export const MAX_BLUR = 40;

export default function MotionFilters({ blur = 0, angle = 0 }) {
  // Split the blur between the two axes according to the direction of travel: a
  // horizontal move blurs only x, a diagonal splits between them.
  const rad = (angle * Math.PI) / 180;
  const bx = Math.abs(Math.cos(rad)) * blur;
  const by = Math.abs(Math.sin(rad)) * blur;

  return (
    <svg
      width="0"
      height="0"
      style={{ position: 'absolute', pointerEvents: 'none' }}
      aria-hidden="true"
    >
      <defs>
        {/* The pad is generous: a Gaussian spreads the result past the element's
            own bounds, and the default 10% clip leaves a hard edge where the smear
            is cut off. */}
        <filter
          id="motion"
          x="-25%"
          y="-25%"
          width="150%"
          height="150%"
          colorInterpolationFilters="sRGB"
        >
          <feGaussianBlur stdDeviation={`${bx.toFixed(2)} ${by.toFixed(2)}`} />
        </filter>
      </defs>
    </svg>
  );
}
