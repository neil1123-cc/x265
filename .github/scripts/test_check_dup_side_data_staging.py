#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_dup_side_data_staging.py')

# Coverage probes used by the scan for duplication side-data staging guardrails.
NORMALIZED_PROBES = (
    'dup side-data copy must stage new data before clearing and replacing dest state',
    'missing dup side-data staging guardrail: ',
    """forbidden dup side-data staging regression: clearDupPictureSideData(dest);

    if (src->userSEI.numPayloads < 0)""",
    """forbidden dup side-data staging regression: clearDupPictureSideData(dest);
                return false;""",
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
                    'x265_picture stagedSideData = {};',
                    'stagedSideData.userSEI.payloads = new (std::nothrow) x265_sei_payload[src->userSEI.numPayloads];',
                    'clearDupPictureSideData(&stagedSideData);',
                    'stagedSideData.rpu.payload = new (std::nothrow) uint8_t[src->rpu.payloadSize];',
                    'clearDupPictureSideData(dest);',
                    'dest->userSEI = stagedSideData.userSEI;',
                    'dest->rpu = stagedSideData.rpu;',
                    'stagedSideData.userSEI.payloads = nullptr;',
                    'stagedSideData.rpu.payload = nullptr;',
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
                    'clearDupPictureSideData(dest);',
                    'if (src->userSEI.numPayloads < 0)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing dup side-data staging guardrail')

    print('Duplication side-data staging tests passed')


if __name__ == '__main__':
    main()
