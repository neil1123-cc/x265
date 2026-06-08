#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_pools_exclude_both_sockets_guard.py')

# Coverage probes used by the scan for SVT pools exclude-both-sockets guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT pools exclude-both-sockets regression: invalid pools input must surface a parse error',
    'missing SVT pools exclude-both-sockets guardrail: ',
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
                    'else if (!strcmp(temp2, "-"))',
                    '{',
                    '    x265_log(param, X265_LOG_ERROR, "Shouldn\'t exclude both sockets for pools option %s \\n", pools);',
                    '    bError = true;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'else if (!strcmp(temp2, "-")) x265_log(param, X265_LOG_ERROR, "Shouldn\'t exclude both sockets for pools option %s \\n", pools);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT pools exclude-both-sockets regression')

    print('SVT pools exclude-both-sockets guard tests passed')


if __name__ == '__main__':
    main()
