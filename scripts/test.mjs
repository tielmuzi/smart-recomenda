import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const pythonExecutable = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python');

if (!existsSync(pythonExecutable)) {
  console.error('Ambiente virtual não encontrado. Execute "pnpm setup" antes de rodar os testes.');
  process.exit(1);
}

const result = spawnSync(pythonExecutable, ['-m', 'pytest', '-q', 'backend/tests'], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

if (result.error) {
  console.error(result.error);
  process.exit(1);
}

process.exit(result.status ?? 0);
