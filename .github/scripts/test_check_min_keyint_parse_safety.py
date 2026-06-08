#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_min_keyint_parse_safety.py')


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
                    'OPT("min-keyint")',
                    '{',
                    '    bool bKeyframeMinError = false;',
                    '    int keyframeMin = parseOptionIntValue(value, bKeyframeMinError);',
                    '    bError |= bKeyframeMinError;',
                    '    if (!bKeyframeMinError)',
                    '        p->keyframeMin = keyframeMin;',
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
                'source/common/param.cpp': '\n'.join((
                    'OPT("min-keyint")',
                    '{',
                    '    int keyframeMin = parseOptionIntValue(value, bKeyframeMinError);',
                    '    bError |= bKeyframeMinError;',
                    '    if (!bKeyframeMinError)',
                    '        p->keyframeMin = keyframeMin;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing min-keyint guardrail: bool bKeyframeMinError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("min-keyint") p->keyframeMin = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden min-keyint regression: invalid values must not overwrite prior state')

    print('Min-keyint parse safety tests passed')


if __name__ == '__main__':
    main()
