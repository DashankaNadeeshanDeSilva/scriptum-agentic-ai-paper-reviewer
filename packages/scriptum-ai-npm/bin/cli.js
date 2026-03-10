#!/usr/bin/env node

/**
 * SCRIPTUM npx wrapper
 *
 * Usage:  npx scriptum-ai@latest
 *         npx scriptum-ai start --port 9000
 *         npx scriptum-ai doctor
 *
 * On first run this script:
 *   1. Checks that Python >= 3.11 is available
 *   2. Creates a virtual environment at ~/.scriptum/venv
 *   3. Installs the scriptum-ai pip package into it
 *   4. Runs `scriptum start` (or whatever sub-command was passed)
 *
 * Subsequent runs skip steps 2-3 and start immediately.
 */

const { execSync, spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

// ── Constants ───────────────────────────────────────────────────────────

const SCRIPTUM_HOME = path.join(os.homedir(), ".scriptum");
const VENV_DIR = path.join(SCRIPTUM_HOME, "venv");
const PIP_PACKAGE = "scriptum-ai";
const MIN_PYTHON_MAJOR = 3;
const MIN_PYTHON_MINOR = 11;

// ── Helpers ─────────────────────────────────────────────────────────────

function log(msg) {
  console.log(`\x1b[36m[scriptum]\x1b[0m ${msg}`);
}

function error(msg) {
  console.error(`\x1b[31m[scriptum] ERROR:\x1b[0m ${msg}`);
}

/**
 * Try multiple python command names and return the first one that
 * satisfies the minimum version requirement.
 */
function findPython() {
  const candidates = ["python3", "python"];

  for (const cmd of candidates) {
    try {
      const raw = execSync(`${cmd} --version 2>&1`, { encoding: "utf-8" }).trim();
      // "Python 3.12.1"
      const match = raw.match(/Python (\d+)\.(\d+)/);
      if (!match) continue;

      const major = parseInt(match[1], 10);
      const minor = parseInt(match[2], 10);

      if (major > MIN_PYTHON_MAJOR || (major === MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR)) {
        return { cmd, version: raw };
      }
    } catch {
      // command not found — try next
    }
  }
  return null;
}

/**
 * Return the path to the `scriptum` CLI inside the managed venv.
 */
function scriptumBin() {
  const isWindows = process.platform === "win32";
  const binDir = isWindows ? "Scripts" : "bin";
  return path.join(VENV_DIR, binDir, "scriptum");
}

/**
 * Return the path to `pip` inside the managed venv.
 */
function pipBin() {
  const isWindows = process.platform === "win32";
  const binDir = isWindows ? "Scripts" : "bin";
  return path.join(VENV_DIR, binDir, "pip");
}

/**
 * Return the path to `python` inside the managed venv.
 */
function venvPython() {
  const isWindows = process.platform === "win32";
  const binDir = isWindows ? "Scripts" : "bin";
  return path.join(VENV_DIR, binDir, isWindows ? "python.exe" : "python");
}

/**
 * Run a command synchronously and stream output to the user's terminal.
 * Returns true on success.
 */
function run(cmd, args, opts = {}) {
  const result = spawn(cmd, args, {
    stdio: "inherit",
    ...opts,
  });

  return new Promise((resolve) => {
    result.on("close", (code) => resolve(code === 0));
    result.on("error", () => resolve(false));
  });
}

// ── Main ────────────────────────────────────────────────────────────────

async function main() {
  // 1. Find a suitable Python
  const python = findPython();
  if (!python) {
    error(
      `Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required but was not found.\n` +
      "  Install it from https://www.python.org/downloads/ and make sure it's on your PATH."
    );
    process.exit(1);
  }

  // 2. Ensure ~/.scriptum/ exists
  fs.mkdirSync(SCRIPTUM_HOME, { recursive: true });

  // 3. Create venv if it doesn't exist
  const needsSetup = !fs.existsSync(venvPython());
  if (needsSetup) {
    log(`Setting up SCRIPTUM (Python ${python.version})...`);
    log(`Creating virtual environment at ${VENV_DIR}`);

    const venvOk = await run(python.cmd, ["-m", "venv", VENV_DIR]);
    if (!venvOk) {
      error("Failed to create virtual environment.");
      process.exit(1);
    }
  }

  // 4. Install / upgrade scriptum-ai if needed
  const scriptumExists = fs.existsSync(scriptumBin()) || fs.existsSync(scriptumBin() + ".exe");
  if (!scriptumExists || needsSetup) {
    log(`Installing ${PIP_PACKAGE}...`);

    const installOk = await run(pipBin(), ["install", "--upgrade", PIP_PACKAGE]);
    if (!installOk) {
      error(
        `Failed to install ${PIP_PACKAGE}.\n` +
        `  You can try manually: ${pipBin()} install ${PIP_PACKAGE}`
      );
      process.exit(1);
    }

    log("Installation complete!");
  }

  // 5. Forward CLI args to the scriptum command
  //    npx scriptum-ai start --port 9000  →  scriptum start --port 9000
  //    npx scriptum-ai                    →  scriptum start  (default)
  const userArgs = process.argv.slice(2);
  const args = userArgs.length > 0 ? userArgs : ["start"];

  log(`Running: scriptum ${args.join(" ")}`);

  const ok = await run(scriptumBin(), args);
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  error(err.message || String(err));
  process.exit(1);
});
