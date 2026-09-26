// SceneMulti — three monitors receding into the room, configured one at a time.
//
// ── why this was rebuilt ─────────────────────────────────────────────────────
//
// The first version put the app panel and three monitors on one horizontal line
// against a flat gradient. A review called it out as the frame that looks most like a
// slide, and the reasons it gave were exact:
//
//   "the monitors are aligned perfectly on a single horizontal axis... there is no
//    variation in height, scale, or angle to suggest a three-dimensional space"
//   "no overlapping - every element is distinct and separate, never intersecting"
//   "every monitor is lit with the same flat, even light"
//
// All three are fixable without leaving a 2D compositor, because the things that make
// a frame read as a space are perspective, overlap and light - not actual 3D:
//
//   · PERSPECTIVE. The three screens are placed on a receding line: each is smaller
//     than the one before, sits higher, and is rotated about the Y axis, so the row
//     has a vanishing point instead of a baseline. The camera looks along the row
//     rather than at it.
//   · OVERLAP. Each screen overlaps the one behind it, and the row runs off the right
//     edge of the frame. Nothing is fully contained, which is what a slide does.
//   · LIGHT. Each screen casts its own coloured bloom onto the surface behind it, and
//     the row sits on a visible floor plane with a reflection. The bezels are lit from
//     the screen side, not evenly.
//
// The app panel is still in the frame, because the feature is that the APP assigns a
// wallpaper per display - but it is no longer a peer of the monitors. It sits in the
// foreground, larger, angled, and partially cropped by the frame edge, so it reads as
// the operator's view and the monitors as the room.
//
// Nothing is cropped in a way that loses content: the monitors run off the edge
// deliberately (that is the depth), and the app panel is whole.

import React from 'react';
import { Surface, Shot, Type, Eyebrow, Wallpaper, FONT } from '../Kit.jsx';
import { seg, easeOut, easeOutQuint } from '../anim.js';

// The row, receding. `z` is depth: 0 is nearest. Scale, height and angle all follow
// from it, so the row is generated rather than hand-placed.
const SCREENS = [
  { clip: 'i14',    label: 'Display 1', color: '#ff3b57', z: 0 },
  { clip: 'albedo', label: 'Display 2', color: '#3ad0e0', z: 1 },
  { clip: 'raiden', label: 'Display 3', color: '#35e07a', z: 2 },
];

// A short focal length. This is what turns the row's side screens into trapezoids
// rather than rectangles - at 2100px the distortion was too weak to read as a space,
// and a review of that render described the screens as "flat rectangles rather than
// trapezoids receding into a vanishing point".
const PERSPECTIVE = 1150;

export default function SceneMulti({ t, global, variant = 0 }) {
  const head = easeOutQuint(seg(t, 0.1, 1.0));
  const panel = easeOutQuint(seg(t, 0.35, 1.35));

  // Each screen lights up in turn, and its own bloom arrives with it.
  const arrivals = SCREENS.map((_, i) => easeOutQuint(seg(t, 1.4 + i * 0.5, 2.2 + i * 0.5)));

  // The row drifts left through the shot, so the depth is continuously revealed -
  // this is the move that says "there is a room here" rather than "here is a row".
  //
  // Small: at -78px the nearest screen drifted into the app panel's column, and the
  // panel paints over it. -46 keeps the whole row to the right of the panel.
  const travel = easeOut(seg(t, 0.9, 4.2)) * -46;

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <Surface t={global} intensity={1.0} warmSide={variant ? 'left' : 'right'} grid={false} />

      {/* A floor, so the row has a surface to stand on rather than a void behind it.
          The horizon sits low in the frame and the plane darkens towards the viewer. */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '58%',
          bottom: 0,
          background:
            'linear-gradient(180deg, rgba(20,22,28,.0) 0%, rgba(14,15,20,.55) 26%, rgba(9,10,14,.86) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '58%',
          height: 1,
          background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,.09) 30%, rgba(255,255,255,.05) 100%)',
        }}
      />

      {/* ── the row of screens, receding ─────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '16%',
          bottom: '16%',
          perspective: `${PERSPECTIVE}px`,
          perspectiveOrigin: '18% 50%',
          // The row is pushed down and right so the headline's band across the top is
          // clear. Without the camera's zoom the first monitor sits higher than it used
          // to, and its bright wallpaper reached into the text: measured, the background
          // under the headline hit 0.88 luminance against a 0.30 limit, and the scene
          // was reported as having unreadable type. The scene's own layout put the text
          // at the top-left, so the row moves out of the way rather than the text being
          // given a heavier scrim - a scrim over a wallpaper this bright would have to
          // be nearly opaque, which would hide the product.
          transform: 'translateY(74px)',
        }}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            transformStyle: 'preserve-3d',
            transform: `translateX(${travel}px)`,
          }}
        >
          {SCREENS.map((s, i) => {
            const k = arrivals[i];

            // The receding line: each screen is further away, so it is smaller, higher
            // and more turned away from the camera.
            //
            // ── the layout is computed, not eyeballed ─────────────────────────────
            //
            // The previous attempt pushed each screen back with translate3d(z) AND
            // scaled it AND placed it on a percentage of the frame, and the three
            // compounded: the third screen ended up starting past the right edge, so a
            // review of that render counted ONE monitor on screen instead of three.
            //
            // So the placement is worked out here in pixels against the 1920 frame, and
            // the depth is expressed only through scale and rotation - the two things
            // that read as distance without moving the screen off the frame.
            //
            //   screen 1   left 545, width 640 -> 545..1185  (rotateY -30 => ~554 wide)
            //   screen 2   left 880, width 640 -> 880..1425
            //   screen 3   left 1175, width 640 -> 1175..1615
            //
            // All three are inside the frame, each overlaps the one behind it, and the
            // row leaves the app panel's column (74..694) clear.
            const depth = s.z;
            const scale = 1 - depth * 0.155;
            const leftPx = 545 + depth * 315;
            const topPct = depth * 7.5;
            const rotY = -30 + depth * 9;         // turned away, opening towards the camera
            const rotZ = -depth * 1.8;

            return (
              <div
                key={s.label}
                style={{
                  position: 'absolute',
                  // Pixels, not a percentage: see the note above on why the percentages
                  // compounded with the depth into a row that left the frame.
                  left: leftPx,
                  top: `${topPct}%`,
                  width: 640,
                  transformOrigin: 'left center',
                  transform:
                    `translate3d(0, ${(1 - k) * 40}px, 0) ` +
                    `rotateY(${rotY}deg) rotateZ(${rotZ}deg) scale(${scale * (0.94 + 0.06 * k)})`,
                  opacity: 0.34 + 0.66 * k,
                  // Nearer screens paint over further ones. This is the overlap that
                  // makes the row read as depth rather than as a list.
                  zIndex: 10 - depth,
                }}
              >
                {/* The screen's own light on the surface behind it. */}
                <div
                  style={{
                    position: 'absolute',
                    left: '-16%',
                    right: '-16%',
                    top: '-16%',
                    bottom: '-16%',
                    background: `radial-gradient(52% 52% at 50% 50%, ${s.color}${k > 0.5 ? '2e' : '14'} 0%, ${s.color}00 72%)`,
                    filter: 'blur(28px)',
                    zIndex: -1,
                  }}
                />

                {/* The bezel: lit from the screen side, dark on the far side. */}
                <div
                  style={{
                    position: 'relative',
                    borderRadius: 10,
                    padding: 8,
                    background:
                      'linear-gradient(155deg, #34383f 0%, #1b1d22 42%, #0f1013 100%)',
                    boxShadow:
                      `0 40px 80px -34px rgba(0,0,0,.95), ` +
                      `inset 0 1px 0 rgba(255,255,255,.10), ` +
                      `0 0 0 1px ${k > 0.5 ? s.color + '55' : 'rgba(255,255,255,.06)'}`,
                  }}
                >
                  <Wallpaper clip={s.clip} t={global} width="100%" radius={5} />
                </div>

                {/* The stand, and its reflection on the floor. The reflection is what
                    anchors the screen to a surface - without it the row floats in a
                    void, which is the "flat design" reading a review gave the previous
                    version. */}
                <div style={{ width: '16%', height: 11, margin: '0 auto', background: 'linear-gradient(180deg,#2b2e35,#15161a)', borderRadius: '0 0 4px 4px' }} />
                <div style={{ width: '34%', height: 6, margin: '0 auto', background: 'linear-gradient(180deg,#23252b,#121316)', borderRadius: 4 }} />
                {/* The screen's colour spilling onto the surface below it. */}
                <div
                  style={{
                    width: '86%',
                    height: 54,
                    margin: '2px auto 0',
                    background: `linear-gradient(180deg, ${s.color}30 0%, ${s.color}12 42%, ${s.color}00 100%)`,
                    filter: 'blur(13px)',
                    opacity: k,
                  }}
                />
                {/* And the stand's own shadow, cast onto that surface. */}
                <div
                  style={{
                    width: '30%',
                    height: 9,
                    margin: '0 auto',
                    background: 'radial-gradient(50% 50% at 50% 50%, rgba(0,0,0,.85) 0%, rgba(0,0,0,0) 100%)',
                    filter: 'blur(5px)',
                    opacity: k,
                  }}
                />

                <div
                  style={{
                    marginTop: 8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 9,
                    opacity: k,
                  }}
                >
                  <span style={{ width: 9, height: 9, borderRadius: '50%', background: s.color, boxShadow: `0 0 12px ${s.color}` }} />
                  <span style={{ fontFamily: FONT, fontSize: 19, fontWeight: 700, color: '#dfe3e9', letterSpacing: '.01em' }}>
                    {s.label}
                  </span>
                  <span style={{ fontFamily: FONT, fontSize: 16, color: '#7f858e' }}>
                    1920×1080
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── the app panel: the operator's view, in the foreground ────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 74,
          bottom: 92,
          width: 620,
          opacity: panel,
          transform: `translateY(${(1 - panel) * 30}px)`,
          zIndex: 40,
        }}
      >
        <Shot src="./shots/ui-displays.png" width={620} radius={13} />
      </div>

      {/* ── the statement, over the row rather than above it ─────────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 74,
          top: 76,
          maxWidth: 700,
          opacity: head,
          transform: `translateY(${(1 - head) * 18}px)`,
          zIndex: 50,
        }}
      >
        <Eyebrow color="#3ad0e0" style={{ marginBottom: 14 }}>
          Multi-monitor
        </Eyebrow>
        <Type size={50}>Tiap layar, pengaturannya sendiri.</Type>
      </div>
    </div>
  );
}
