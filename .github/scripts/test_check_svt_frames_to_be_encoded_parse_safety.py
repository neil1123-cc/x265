#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_frames_to_be_encoded_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing SVT frames-to-be-encoded guardrail: ',
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


PASS_SOURCE = '\n'.join((
    'OPT("total-frames")',
    '{',
    '    bool bFramesToBeEncodedError = false;',
    '    int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);',
    '    bError |= bFramesToBeEncodedError;',
    '    if (!bFramesToBeEncodedError)',
    '        svtHevcParam->framesToBeEncoded = framesToBeEncoded;',
    '}',
    'OPT("frames")',
    '{',
    '    bool bFramesToBeEncodedError = false;',
    '    int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);',
    '    bError |= bFramesToBeEncodedError;',
    '    if (!bFramesToBeEncodedError)',
    '        svtHevcParam->framesToBeEncoded = framesToBeEncoded;',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("total-frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);',
                    'OPT("frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT total-frames regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("total-frames")',
                    '{',
                    '    bool bFramesToBeEncodedError = false;',
                    '    int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);',
                    '    bError |= bFramesToBeEncodedError;',
                    '    if (!bFramesToBeEncodedError)',
                    '        svtHevcParam->framesToBeEncoded = framesToBeEncoded;',
                    '}',
                    'OPT("frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT frames regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'bool bFramesToBeEncodedError = false;',
                    'bool bOtherFramesError = false;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing SVT frames-to-be-encoded guardrail in both aliases')

    print('SVT frames-to-be-encoded parse safety tests passed')


if __name__ == '__main__':
    main()
