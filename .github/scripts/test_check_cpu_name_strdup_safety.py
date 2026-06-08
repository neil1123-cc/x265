#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cpu_name_strdup_safety.py')

# Coverage probes used by the scan for parseCpuName strdup guardrails.
NORMALIZED_PROBES = (
    'parseCpuName must check strdup failure before scanning tokens',
    'forbidden parseCpuName strdup regression: ',
    'missing parseCpuName strdup guardrail: ',
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
                'source/common/param.cpp': '\n'.join((
                    'char *buf = strdup(value);',
                    'if (!buf)',
                    '{',
                    '    bError = 1;',
                    '    return 0;',
                    '}',
                    'for (char* scan = buf; scan && *scan; )',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'char *buf = strdup(value);',
                    'char *tok;',
                    'bError = 0;',
                    'cpu = 0;',
                    'for (char* scan = buf; scan && *scan; )',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing parseCpuName strdup guardrail')

    print('parseCpuName strdup safety tests passed')


if __name__ == '__main__':
    main()
