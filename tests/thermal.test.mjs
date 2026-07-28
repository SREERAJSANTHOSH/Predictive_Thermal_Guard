import assert from "node:assert/strict";
import test from "node:test";

import { createDemoFrame, thermalColor } from "../lib/thermal.mjs";

test("demo frame has the requested dimensions and a central hotspot", () => {
  const frame = createDemoFrame(24, 16);

  assert.equal(frame.length, 384);
  assert.ok(Math.max(...frame) > 70);
  assert.ok(Math.min(...frame) >= 20);
});

test("thermal colour scale clamps values outside its display range", () => {
  assert.equal(thermalColor(-20), "rgb(8,32,88)");
  assert.equal(thermalColor(120), "rgb(255,246,218)");
  assert.match(thermalColor(65), /^rgb\(\d+,\d+,\d+\)$/);
});
