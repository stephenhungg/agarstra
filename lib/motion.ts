/** Measured from the live Fabrica reference. See reference/motion-audit.md. */
export const motion = {
  entranceEase: "fabrica-entrance",
  entranceCurve: "0.96,-0.02,0.38,1.01",
  hoverEase: "fabrica-hover",
  hoverCurve: "0.82,0.11,0.37,0.82",
  characterDuration: 0.4,
  characterDelay: 0.3,
  characterStagger: 0.09,
  textDuration: 0.9,
  textStagger: 0.02,
  menuDuration: 0.5,
  hoverDuration: 0.45,
} as const;

// Normalized analytical springs avoid substituting an unrelated power ease.
// Source hero: duration 1, bounce 0; shared reveals: duration 1.2, bounce .1.
export const heroSpring = (progress: number) => {
  const settle = (t: number) => 1 - (1 + 8 * t) * Math.exp(-8 * t);
  return settle(progress) / settle(1);
};
export const revealSpring = (progress: number) => {
  const settle = (t: number) =>
    1 - Math.exp(-7 * t) * (Math.cos(4 * t) + 1.75 * Math.sin(4 * t));
  return settle(progress) / settle(1);
};
