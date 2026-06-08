#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_read_user_sei_staging.py')

# Coverage probes used by the scan for readUserSei staging guardrails.
NORMALIZED_PROBES = (
    'readUserSeiFile must validate payload type and stage payload before committing seiMsg',
    'forbidden readUserSei staging regression: ',
    'missing readUserSei staging guardrail: ',
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
                    'SEIPayloadType stagedPayloadType;',
                    'uint8_t* stagedPayload = (uint8_t*)x265_malloc(decodedSize);',
                    'std::memcpy(stagedPayload, base64Decode, decodedSize);',
                    'seiMsg.payloadSize = (int)decodedSize;',
                    'seiMsg.payload = stagedPayload;',
                    'seiMsg.payloadType = stagedPayloadType;',
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
                    'seiMsg.payloadSize = (int)decodedSize;',
                    'seiMsg.payload = (uint8_t*)x265_malloc(decodedSize);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing readUserSei staging guardrail')

    print('readUserSeiFile staging tests passed')


if __name__ == '__main__':
    main()
