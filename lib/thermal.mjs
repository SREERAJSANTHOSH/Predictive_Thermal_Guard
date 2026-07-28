const COLOR_STOPS = [
  [20, [8, 32, 88]],
  [35, [0, 135, 180]],
  [50, [55, 190, 118]],
  [65, [247, 205, 45]],
  [80, [255, 91, 35]],
  [100, [255, 246, 218]],
];

export function createDemoFrame(width, height) {
  return Array.from({ length: width * height }, (_, index) => {
    const x = index % width;
    const y = Math.floor(index / width);
    const base = 28 + y * 0.65 + Math.sin(x * 0.72) * 2.8;
    const phase1 = 14 * Math.exp(-((x - 6) ** 2 + (y - 8) ** 2) / 18);
    const phase2 = 46 * Math.exp(-((x - 12) ** 2 + (y - 7) ** 2) / 13);
    const phase3 = 18 * Math.exp(-((x - 18) ** 2 + (y - 9) ** 2) / 20);
    return Number((base + phase1 + phase2 + phase3).toFixed(1));
  });
}

export function thermalColor(value) {
  for (let index = 1; index < COLOR_STOPS.length; index += 1) {
    const [upperValue, upperColor] = COLOR_STOPS[index];
    const [lowerValue, lowerColor] = COLOR_STOPS[index - 1];
    if (value <= upperValue) {
      const ratio = Math.max(
        0,
        Math.min(1, (value - lowerValue) / (upperValue - lowerValue)),
      );
      const rgb = lowerColor.map((channel, colorIndex) =>
        Math.round(channel + (upperColor[colorIndex] - channel) * ratio),
      );
      return `rgb(${rgb.join(",")})`;
    }
  }
  return "rgb(255,246,218)";
}
