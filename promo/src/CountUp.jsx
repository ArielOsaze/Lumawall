// CountUp — a number that counts to its value.
//
// A pure function of time, so the count is identical on every render. Counting
// makes a comparison land: the viewer watches one figure climb while the other
// stays flat, instead of reading two static numbers.

import React from 'react';
import { seg, easeOutExpo } from './anim.js';

export default function CountUp({
  to,
  t,
  from = 0,
  delay = 0,
  dur = 1.2,
  decimals = 0,
  suffix = '',
  prefix = '',
  style = {},
}) {
  const k = easeOutExpo(seg(t, delay, delay + dur));
  const value = from + (to - from) * k;

  return (
    <span style={style}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}
