#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_frame_read_state.py')


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
    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
    'if (!rowBytes && std::feof(file) && !i)',
    'ret = 2;',
    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
    'if (!rowWords && std::feof(file) && !i)',
    'ret = 2;',
    'if (ret == 2)',
    '{',
    '    x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");',
    '    return 1;',
    '}',
    '// reference skip u and v',
    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
    'return 1;',
    '// distorted skip u and v',
    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
    'return 1;',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': 'if (feof(user_data->reference_file))\n'})
        expect_fail(run_checker(root), 'forbidden VMAF frame read regression: if (feof(user_data->reference_file))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
                    'ret = 2;',
                    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
                    'if (!rowWords && std::feof(file) && !i)',
                    'ret = 2;',
                    'if (ret == 2)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");',
                    '    return 1;',
                    '}',
                    '// reference skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
                    'return 1;',
                    '// distorted skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
                    'return 1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing VMAF frame read guardrail: if (!rowBytes && std::feof(file) && !i)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
                    'ret = 2;',
                    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
                    'if (!rowWords && std::feof(file) && !i)',
                    'ret = 2;',
                    'if (ret == 2)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");',
                    '    return 1;',
                    '}',
                    '// reference skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
                    'return 1;',
                    '// distorted skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
                    'return 1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF 8-bit frame reads must only treat a zero-byte first-row EOF as a clean end-of-stream')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
                    'if (!rowBytes && std::feof(file) && !i)',
                    'ret = 2;',
                    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
                    'if (!rowWords && std::feof(file) && !i)',
                    'ret = 2;',
                    'if (ret == 2)',
                    '{',
                    '    return 1;',
                    '}',
                    '// reference skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
                    'return 1;',
                    '// distorted skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
                    'return 1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF read_frame must reject distorted-input EOF after a reference frame has already been read')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
                    'if (!rowBytes && std::feof(file) && !i)',
                    'ret = 2;',
                    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
                    'if (!rowWords && std::feof(file) && !i)',
                    'ret = 2;',
                    'if (ret == 2)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");',
                    '    return 1;',
                    '}',
                    '// reference skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
                    '// distorted skip u and v',
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
                    'return 1;',
                    'return 1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF read_frame must fail fast when skipping reference chroma data fails')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': PASS_SOURCE.replace(
                    'if (!rowWords && std::feof(file) && !i)\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'VMAF 10-bit frame reads must only treat a zero-word first-row EOF as a clean end-of-stream')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': PASS_SOURCE.replace(
                    '// distorted skip u and v\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");\n'
                    'return 1;\n',
                    '// distorted skip u and v\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'VMAF read_frame must fail fast when skipping distorted chroma data fails')

    print('VMAF frame read state tests passed')


if __name__ == '__main__':
    main()
