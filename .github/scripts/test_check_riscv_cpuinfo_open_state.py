#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_riscv_cpuinfo_open_state.py')

# Coverage probes used by the scan for RISC-V cpuinfo open-state guardrails.
NORMALIZED_PROBES = (
    'riscv cpuinfo open-state guard must follow the null check before file reads',
    'missing riscv cpuinfo open-state guardrail: ',
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
                    'FILE *file = fopen("/proc/cpuinfo", "r");',
                    'if (file == nullptr)',
                    '    return 0;',
                    'else if (ferror(file)) {',
                    '    int closeFailed = ferror(file) != 0;',
                    '    if (fclose(file))',
                    '        closeFailed = 1;',
                    '    if (closeFailed)',
                    '        return 0;',
                    '    return 0;',
                    'char line[1024];',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/riscv64/cpu.h': 'FILE *file = fopen("/proc/cpuinfo", "r");\nif (file == nullptr)\n    return 0;\nchar line[1024];\n',
            },
        )
        expect_fail(run_checker(root), 'missing riscv cpuinfo open-state guardrail')

    print('RISC-V cpuinfo open-state guard tests passed')


if __name__ == '__main__':
    main()
