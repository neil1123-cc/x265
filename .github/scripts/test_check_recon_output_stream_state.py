#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_recon_output_stream_state.py')

# Coverage probes used by the scan for recon output stream-state guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing recon output stream-state guardrail: ',
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
                'source/output/y4m.cpp': '\n'.join((
                    'if (!buf || !ofs || failed)',
                    '    return false;',
                    'return !failed;',
                )) + '\n',
                'source/output/yuv.cpp': '\n'.join((
                    'if (!buf || !ofs || failed)',
                    '    return false;',
                    'return !failed;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/y4m.cpp': 'return true;\n',
                'source/output/yuv.cpp': 'return true;\n',
            },
        )
        expect_fail(run_checker(root), 'missing recon output stream-state guardrail')

    print('Recon output stream-state guard tests passed')


if __name__ == '__main__':
    main()
