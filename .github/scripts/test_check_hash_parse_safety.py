#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_hash_parse_safety.py')


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
                    'OPT("hash")',
                    '{',
                    '    bool bDecodedPictureHashSEIError = false;',
                    '    int decodedPictureHashSEI = parseOptionIntValue(value, bDecodedPictureHashSEIError);',
                    '    bError |= bDecodedPictureHashSEIError;',
                    '    if (!bDecodedPictureHashSEIError)',
                    '        p->decodedPictureHashSEI = decodedPictureHashSEI;',
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
                    'OPT("hash")',
                    '{',
                    '    int decodedPictureHashSEI = parseOptionIntValue(value, bDecodedPictureHashSEIError);',
                    '    bError |= bDecodedPictureHashSEIError;',
                    '    if (!bDecodedPictureHashSEIError)',
                    '        p->decodedPictureHashSEI = decodedPictureHashSEI;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing hash guardrail: bool bDecodedPictureHashSEIError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("hash") p->decodedPictureHashSEI = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden hash regression: invalid values must not overwrite prior state')

    print('Hash parse safety tests passed')


if __name__ == '__main__':
    main()
