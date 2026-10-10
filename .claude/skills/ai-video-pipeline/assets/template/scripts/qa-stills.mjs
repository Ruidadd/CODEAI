// Render one still per scene (middle frame) so the layout can be checked
// without rendering the whole video. Bundles once, then renders each frame.
//
//   node scripts/qa-stills.mjs <manifest path inside public/> [out dir]
//   node scripts/qa-stills.mjs demo/manifest.json out/qa
//
// Set REMOTION_BROWSER_EXECUTABLE to use an already-installed Chromium.

import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

const manifestPath = process.argv[2] ?? "demo/manifest.json";
const outDir = process.argv[3] ?? "out/qa";
const manifest = JSON.parse(
  readFileSync(path.join("public", manifestPath), "utf8"),
);
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE ?? null;
const inputProps = { manifestPath };

const serveUrl = await bundle({
  entryPoint: path.resolve("src/index.ts"),
  publicDir: path.resolve("public"),
});
const composition = await selectComposition({
  serveUrl,
  id: "StoryboardVideo",
  inputProps,
  browserExecutable,
});

mkdirSync(outDir, { recursive: true });
for (const scene of manifest.scenes) {
  const frame = scene.from + Math.floor(scene.durationInFrames / 2);
  const output = path.join(outDir, `${scene.id}.png`);
  await renderStill({
    composition,
    serveUrl,
    output,
    frame,
    inputProps,
    browserExecutable,
    scale: 0.5,
  });
  console.log(`${scene.id}\tframe ${frame}\t${output}`);
}
