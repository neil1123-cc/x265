#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encode_quant_offsets_staging.py')

# Coverage probes used by the scan for encode quantOffsets staging guardrails.
NORMALIZED_PROBES = (
    'forbidden encode quantOffsets staging regression: ',
    'missing encode quantOffsets staging guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (inputPic[0]->quantOffsets != nullptr)',
                    '    return -1;',
                    'copyUserSEIMessages(inFrame[0], inputPic[0]);',
                    'if (inputPic[0]->rpu.payloadSize < 0)',
                    '    return -1;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'copyUserSEIMessages(inFrame[0], inputPic[0]);',
                    'if (inputPic[0]->rpu.payloadSize < 0)',
                    '    return -1;',
                    'if (inputPic[0]->quantOffsets != nullptr)',
                    '    return -1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'encode must reject quantOffsets before copying user SEI messages and Dolby Vision RPU state')

    print('encode quantOffsets staging tests passed')


if __name__ == '__main__':
    main()
