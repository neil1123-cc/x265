#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_raw_output_write_guard.py')

# Coverage probes used by the scan for raw output write guardrails.
NORMALIZED_PROBES = (
    'RAW output must guard fwrite results in both header and frame writers',
    'missing RAW output write guardrail: ',
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
                'source/output/raw.cpp': '\n'.join((
                    'size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);',
                    'if (written != nal->sizeBytes || std::ferror(ofs))',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);',
                    'if (written != nal->sizeBytes || std::ferror(ofs))',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/raw.cpp': 'std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);\n'})
        expect_fail(run_checker(root), 'missing RAW output write guardrail')

    print('RAW output write guard tests passed')


if __name__ == '__main__':
    main()
