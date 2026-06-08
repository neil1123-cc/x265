#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_copy_user_sei_staging.py')

# Coverage probes used by the scan for copyUserSEI staging guardrails.
NORMALIZED_PROBES = (
    'copyUserSEI must build staged payloads before clearing and replacing the old frame state',
    'forbidden copyUserSEI staging regression: ',
    'missing copyUserSEI staging guardrail: ',
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
                    'auto clearUserSEI = [](x265_sei& userSEI)',
                    'x265_sei stagedUserSEI = {};',
                    'stagedUserSEI.payloads = new (std::nothrow) x265_sei_payload[numPayloads];',
                    'clearUserSEI(stagedUserSEI);',
                    'clearUserSEI(frame->m_userSEI);',
                    'frame->m_userSEI = stagedUserSEI;',
                    'stagedUserSEI.payloads = nullptr;',
                    'stagedUserSEI.numPayloads = 0;',
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
                    'clearFrameUserSEI();',
                    'if (frame->m_userSEI.payloads && numPayloads != frame->m_userSEI.numPayloads)',
                    '    clearFrameUserSEI();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden copyUserSEI staging regression')

    print('copyUserSEI staging tests passed')


if __name__ == '__main__':
    main()
