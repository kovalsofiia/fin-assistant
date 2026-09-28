#!/usr/bin/env node
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const frontendDir = join(root, 'frontend');
const backendDir = join(root, 'backend');
const rootModules = join(root, 'node_modules');
const frontendModules = join(frontendDir, 'node_modules');
const backendVenv = join(backendDir, '.venv');
const isWin = process.platform === 'win32';
const venvPython = join(backendVenv, isWin ? 'Scripts/python.exe' : 'bin/python');
const venvUvicorn = join(backendVenv, isWin ? 'Scripts/uvicorn.exe' : 'bin/uvicorn');

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      shell: isWin,
      ...options,
    });
    child.on('error', reject);
    child.on('exit', (code, signal) => {
      if (code === 0) resolve();
      else if (signal) reject(new Error(`${command} terminated by signal ${signal}`));
      else reject(new Error(`${command} ${args.join(' ')} exited with code ${code}`));
    });
  });
}

function resolvePython() {
  const candidates = isWin
    ? ['python', 'py']
    : ['python3.14', 'python3.13', 'python3.12', 'python3.11', 'python3.10', 'python3'];

  for (const cmd of candidates) {
    const probe = spawnSync(cmd, ['-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'], {
      stdio: 'ignore',
      shell: isWin,
    });
    if (probe.status === 0) return cmd;
  }

  throw new Error(
    'Python 3.10+ is required for the backend. Install it and ensure it is on PATH.',
  );
}

async function ensureRootDeps() {
  if (existsSync(join(rootModules, 'concurrently'))) return;
  console.log('→ Installing root dependencies (pnpm)...');
  await run('pnpm', ['install'], { cwd: root });
}

async function ensureFrontendDeps() {
  if (existsSync(frontendModules)) return;
  console.log('→ Installing frontend dependencies (pnpm)...');
  await run('pnpm', ['install'], { cwd: frontendDir });
}

async function ensureBackendDeps() {
  if (existsSync(backendVenv) && existsSync(venvUvicorn)) return;

  const python = resolvePython();
  console.log(`→ Creating backend virtualenv with ${python} and installing requirements...`);
  await run(python, ['-m', 'venv', '.venv'], { cwd: backendDir });
  await run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip'], { cwd: backendDir });
  await run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt'], {
    cwd: backendDir,
  });
}

async function start() {
  await ensureRootDeps();
  await ensureFrontendDeps();
  await ensureBackendDeps();

  const apiCmd = isWin
    ? `cd /d "${backendDir}" && "${venvUvicorn}" main:app --reload --host 127.0.0.1 --port 8000`
    : `cd "${backendDir}" && "${venvUvicorn}" main:app --reload --host 127.0.0.1 --port 8000`;

  console.log('→ Starting frontend (Vite) and backend (uvicorn)...');
  await run(
    'pnpm',
    [
      'exec',
      'concurrently',
      '-n',
      'web,api',
      '-c',
      'cyan,magenta',
      '--kill-others-on-fail',
      'pnpm --dir frontend dev',
      apiCmd,
    ],
    { cwd: root, env: { ...process.env, FORCE_COLOR: '1' } },
  );
}

start().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
