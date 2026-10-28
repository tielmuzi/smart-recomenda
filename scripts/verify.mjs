import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const pythonExecutable = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python');

const run = (command, args, useShell = false) => {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: 'inherit',
    shell: useShell,
  });

  if (result.error) {
    console.error(result.error);
    process.exit(1);
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

if (!existsSync(pythonExecutable)) {
  console.error('Ambiente virtual não encontrado. Execute "pnpm setup" antes de validar o projeto.');
  process.exit(1);
}

run(pythonExecutable, ['-m', 'pytest', '-q', 'backend/tests']);
run(process.platform === 'win32' ? 'cmd.exe' : 'npx', process.platform === 'win32' ? ['/c', 'npx', 'tsc', '--noEmit'] : ['tsc', '--noEmit']);
run(process.platform === 'win32' ? 'cmd.exe' : 'npx', process.platform === 'win32' ? ['/c', 'npx', 'vite', 'build'] : ['vite', 'build']);
