import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
const venvPath = join(root, '.venv');
const pythonExecutable = process.platform === 'win32'
  ? join(venvPath, 'Scripts', 'python.exe')
  : join(venvPath, 'bin', 'python');

const createVenv = spawnSync(pythonCommand, ['-m', 'venv', venvPath], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

if (createVenv.status !== 0) {
  process.exit(createVenv.status ?? 1);
}

if (!existsSync(pythonExecutable)) {
  console.error('O ambiente virtual foi criado, mas o executável Python não foi encontrado. Verifique a instalação do Python no sistema.');
  process.exit(1);
}

const installRequirements = spawnSync(pythonExecutable, ['-m', 'pip', 'install', '--upgrade', 'pip'], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

if (installRequirements.status !== 0) {
  process.exit(installRequirements.status ?? 1);
}

const installBackend = spawnSync(pythonExecutable, ['-m', 'pip', 'install', '-r', 'backend/requirements.txt'], {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

process.exit(installBackend.status ?? 0);
