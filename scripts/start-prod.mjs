import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const host = process.env.APP_HOST || '0.0.0.0';
const port = Number(process.env.APP_PORT || 8000);

const build = process.platform === 'win32'
  ? spawnSync('cmd.exe', ['/c', 'npx', 'vite', 'build'], { cwd: root, stdio: 'inherit' })
  : spawnSync('npx', ['vite', 'build'], { cwd: root, stdio: 'inherit', shell: false });

if (build.status !== 0) {
  process.exit(build.status ?? 1);
}

const pythonExecutable = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python');

const backend = spawn(pythonExecutable, ['-m', 'uvicorn', 'backend.app.main:app', '--host', host, '--port', String(port)], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
  env: { ...process.env, APP_ENV: process.env.APP_ENV || 'production', APP_HOST: host, APP_PORT: String(port) },
});

backend.on('exit', (code) => {
  process.exit(code ?? 0);
});
