#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_dither_image_null_guards.py')


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
        'void x265_dither_image(x265_picture* picIn, int picWidth, int picHeight, int16_t *errorBuf, int bitDepth)',
        '{',
        '    if (!picIn || !errorBuf)',
        '    {',
        '        fprintf(stderr, "extras [error]: x265_dither_image requires non-null picture and error buffer\\n");',
        '        return;',
        '    }',
        '    const x265_api* api = x265_api_get(0);',
        '    if (!api || sizeof(x265_picture) != api->sizeof_picture)',
        '    {',
        '        fprintf(stderr, "extras [error]: structure size skew, unable to dither\\n");',
        '        return;',
        '    }',
        '    if (picIn->bitDepth <= 8)',
        '        return;',
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
                    '    if (!picIn || !errorBuf)\n'
                    '    {\n'
                    '        fprintf(stderr, "extras [error]: x265_dither_image requires non-null picture and error buffer\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_dither_image null guardrail: if (!picIn || !errorBuf)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!api || sizeof(x265_picture) != api->sizeof_picture)\n',
                    '    if (sizeof(x265_picture) != api->sizeof_picture)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_dither_image null guardrail: if (!api || sizeof(x265_picture) != api->sizeof_picture)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'void x265_dither_image(x265_picture* picIn, int picWidth, int picHeight, int16_t *errorBuf, int bitDepth)',
                    '{',
                    '    const x265_api* api = x265_api_get(0);',
                    '    if (!picIn || !errorBuf)',
                    '    {',
                    '        fprintf(stderr, "extras [error]: x265_dither_image requires non-null picture and error buffer\\n");',
                    '        return;',
                    '    }',
                    '    if (!api || sizeof(x265_picture) != api->sizeof_picture)',
                    '    {',
                    '        fprintf(stderr, "extras [error]: structure size skew, unable to dither\\n");',
                    '        return;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_dither_image must reject null picture/error buffer before querying API sizes or dereferencing picture state')

    print('x265_dither_image null guard tests passed')


if __name__ == '__main__':
    main()
