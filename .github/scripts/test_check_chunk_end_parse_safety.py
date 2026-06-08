#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_chunk_end_parse_safety.py')


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
                    'OPT("chunk-end")',
                    '{',
                    '    bool bChunkEndError = false;',
                    '    int chunkEnd = parseOptionIntValue(value, bChunkEndError);',
                    '    const bool bChunkEndRangeError = chunkEnd < 0;',
                    '    bError |= bChunkEndError || bChunkEndRangeError;',
                    '    if (!bChunkEndError && !bChunkEndRangeError)',
                    '        p->chunkEnd = chunkEnd;',
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
                    'OPT("chunk-end")',
                    '{',
                    '    int chunkEnd = parseOptionIntValue(value, bChunkEndError);',
                    '    const bool bChunkEndRangeError = chunkEnd < 0;',
                    '    bError |= bChunkEndError || bChunkEndRangeError;',
                    '    if (!bChunkEndError && !bChunkEndRangeError)',
                    '        p->chunkEnd = chunkEnd;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing chunk-end guardrail: bool bChunkEndError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("chunk-end") p->chunkEnd = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden chunk-end regression: invalid values must not overwrite prior state')

    print('Chunk-end parse safety tests passed')


if __name__ == '__main__':
    main()
