import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const pythonExecutable = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python');

const frontend = process.platform === 'win32'
  ? spawn('cmd.exe', ['/c', 'npx', 'vite', '--host', '0.0.0.0', '--port', '3000'], { cwd: root, stdio: 'inherit' })
  : spawn('npx', ['vite', '--host', '0.0.0.0', '--port', '3000'], { cwd: root, stdio: 'inherit', shell: false });

const backend = spawn(pythonExecutable, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000'], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

const stopAll = () => {
  frontend.kill('SIGINT');
  backend.kill('SIGINT');
  process.exit(0);
};

process.on('SIGINT', stopAll);
process.on('SIGTERM', stopAll);

frontend.on('exit', (code) => {
  if (code !== 0) {
    process.exit(code ?? 1);
  }
  backend.kill('SIGINT');
});

backend.on('exit', (code) => {
  if (code !== 0) {
    process.exit(code ?? 1);
  }
  frontend.kill('SIGINT');
});
