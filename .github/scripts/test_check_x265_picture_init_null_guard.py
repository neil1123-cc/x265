#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_picture_init_null_guard.py')


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


def valid_text():
    return '\n'.join((
        'void x265_picture_init(x265_param *param, x265_picture *pic)',
        '{',
        '    if (!param || !pic)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");',
        '        return;',
        '    }',
        '    std::fill_n(reinterpret_cast<uint8_t*>(pic), sizeof(x265_picture), uint8_t(0));',
        '    pic->bitDepth = param->internalBitDepth;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!param || !pic)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_picture_init null guardrail: if (!param || !pic)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");\n',
                    '        x265_log(nullptr, X265_LOG_ERROR, "bad init\\n");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_picture_init null guardrail: x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'void x265_picture_init(x265_param *param, x265_picture *pic)',
                    '{',
                    '    std::fill_n(reinterpret_cast<uint8_t*>(pic), sizeof(x265_picture), uint8_t(0));',
                    '    if (!param || !pic)',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");',
                    '        return;',
                    '    }',
                    '    pic->bitDepth = param->internalBitDepth;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_picture_init must guard null param/pic before clearing or dereferencing picture state')

    print('x265_picture_init null guard tests passed')


if __name__ == '__main__':
    main()
