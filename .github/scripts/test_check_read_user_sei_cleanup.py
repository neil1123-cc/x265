#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_read_user_sei_cleanup.py')

# Coverage probes used by the scan for readUserSei cleanup guardrails.
NORMALIZED_PROBES = (
    'readUserSeiFile must free decodedString before breaking out of the loop',
    'forbidden readUserSei cleanup regression: ',
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
                    'char *base64Decode = SEI::base64Decode(base64Encode, (int)base64EncodeLength, decodedString);',
                    'bool stopReading = false;',
                    'std::memcpy(stagedPayload, base64Decode, decodedSize);',
                    'std::free(decodedString);',
                    'if (stopReading)',
                    '    break;',
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
                    'char *base64Decode = SEI::base64Decode(base64Encode, (int)base64EncodeLength, decodedString);',
                    'if (base64Decode)',
                    '    std::free(base64Decode);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing readUserSei cleanup guardrail: bool stopReading = false;')

    print('readUserSeiFile cleanup tests passed')


if __name__ == '__main__':
    main()
