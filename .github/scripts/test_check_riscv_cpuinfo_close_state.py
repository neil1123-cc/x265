#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_riscv_cpuinfo_close_state.py')

# Coverage probes used by the scan for RISC-V cpuinfo close-state guardrails.
NORMALIZED_PROBES = (
    'expected two guarded RISC-V cpuinfo fclose calls',
    'forbidden riscv cpuinfo close short-circuit regression: ',
    'missing riscv cpuinfo close guardrail: ',
    'early RISC-V cpuinfo close guard moved out of the open-failure path',
    'final RISC-V cpuinfo close guard moved out of the read loop exit path',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/riscv64/cpu.h': '\n'.join((
                    'else if (ferror(file)) {',
                    'int closeFailed = ferror(file) != 0;',
                    'if (fclose(file))',
                    '    closeFailed = 1;',
                    'if (closeFailed)',
                    '    return 0;',
                    '}',
                    'char line[1024];',
                    'while (fgets(line, sizeof(line), file)) {',
                    '    break;',
                    '}',
                    'int closeFailed = ferror(file) != 0;',
                    'if (fclose(file))',
                    '    closeFailed = 1;',
                    'if (closeFailed)',
                    '    return 0;',
                    'return found;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/riscv64/cpu.h': 'fclose(file);\n'})
        expect_fail(run_checker(root), 'missing riscv cpuinfo close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/riscv64/cpu.h': '\n'.join((
                    'else if (ferror(file)) {',
                    'int closeFailed = ferror(file) != 0;',
                    'if (fclose(file))',
                    '    closeFailed = 1;',
                    'if (closeFailed)',
                    '    return 0;',
                    '}',
                    'char line[1024];',
                    'while (fgets(line, sizeof(line), file)) {',
                    '    break;',
                    '}',
                    'int closeFailed = ferror(file) != 0;',
                    'if (fclose(file))',
                    '    closeFailed = 1;',
                    'if (closeFailed)',
                    '    return 0;',
                    'return found;',
                    'if (ferror(file) || fclose(file))',
                    '    return 0;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden riscv cpuinfo close short-circuit regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/riscv64/cpu.h': '\n'.join((
                    'else if (ferror(file)) {',
                    'int closeFailed = ferror(file) != 0;',
                    'if (fclose(file))',
                    '    closeFailed = 1;',
                    'if (closeFailed)',
                    '    return 0;',
                    '}',
                    'char line[1024];',
                    'while (fgets(line, sizeof(line), file)) {',
                    '    break;',
                    '}',
                    'fclose(file);',
                    'return found;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected two guarded RISC-V cpuinfo close paths')

    print('RISC-V cpuinfo close guard tests passed')


if __name__ == '__main__':
    main()
