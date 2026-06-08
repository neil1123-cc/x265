#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_field_buffer_state_guard.py')

# Coverage probes used by the scan for ABR field-buffer state guardrails.
NORMALIZED_PROBES = (
    'threadMain must keep field-buffer state per invocation and clean it up on exit',
    'missing ABR field-buffer state guardrail: ',
    'forbidden ABR field-buffer state regression: ',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'bool fieldBuffersCreated = false;',
                    'if (!fieldBuffersCreated)',
                    '{',
                    '    fieldBuffersCreated = true;',
                    '}',
                    'if (fieldBuffersCreated)',
                    '{',
                    '    X265_FREE(picField1.planes[0]);',
                    '    X265_FREE(picField2.planes[0]);',
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
                'source/abrEncApp.cpp': 'int static bCreated = 0;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ABR field-buffer state regression')

    print('ABR field-buffer state guard tests passed')


if __name__ == '__main__':
    main()
