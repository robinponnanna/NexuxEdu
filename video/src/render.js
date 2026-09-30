/**
 * CLI Video Renderer Bridge for NexuxEdu.
 * Reads MicroLesson JSON and triggers the authoritative video generator.
 */

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const isDemo = process.argv.includes("--demo");
const rootDir = path.resolve(__dirname, "../..");

console.log("🎬 NexuxEdu Remotion / Video Engine CLI");
console.log(isDemo ? "Mode: Demo Showcase Pre-rendering" : "Mode: Custom Video Render");

// Execute Python video_generator with PYTHONPATH
const pythonExe = process.platform === "win32"
  ? path.join(rootDir, ".venv", "Scripts", "python.exe")
  : path.join(rootDir, ".venv", "bin", "python");

const args = ["-m", "app.services.video_generator"];

const child = spawn(pythonExe, args, {
  cwd: rootDir,
  env: {
    ...process.env,
    PYTHONPATH: path.join(rootDir, "backend")
  },
  stdio: "inherit"
});

child.on("close", (code) => {
  if (code === 0) {
    console.log("✅ Video rendering completed successfully.");
  } else {
    console.error(`❌ Video rendering failed with exit code ${code}`);
  }
  process.exit(code);
});
