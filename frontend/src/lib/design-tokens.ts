/**
 * JS-side mirror of tokens defined in `src/app/globals.css`.
 * Only values that non-CSS consumers (Framer Motion, portaled overlays)
 * actually need at runtime live here. Keep in sync with globals.css.
 */

export const motionDuration = {
  fast: 0.15,
  base: 0.2,
  slow: 0.3,
} as const;

export type MotionDurationToken = keyof typeof motionDuration;

// Mirrors Tailwind's --ease-out / --ease-in / --ease-in-out cubic-beziers.
export const motionEase = {
  out: [0, 0, 0.2, 1],
  in: [0.4, 0, 1, 1],
  inOut: [0.4, 0, 0.2, 1],
} as const;

export type MotionEaseToken = keyof typeof motionEase;

export const zIndex = {
  dropdown: 1000,
  sticky: 1100,
  fixed: 1200,
  modalBackdrop: 1300,
  modal: 1400,
  popover: 1500,
  tooltip: 1600,
  toast: 1700,
} as const;

export type ZIndexToken = keyof typeof zIndex;
