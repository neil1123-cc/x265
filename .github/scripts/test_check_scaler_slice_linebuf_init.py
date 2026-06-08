#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaler_slice_linebuf_init.py')


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
        'int ScalerSlice::create(int lumLines, int crLines, int h_sub_sample, int v_sub_sample, int ring)',
        '{',
        '    m_plane[i].lineBuf = X265_MALLOC(uint8_t*, n);',
        '    if (!m_plane[i].lineBuf)',
        '        return -1;',
        '    std::fill_n(m_plane[i].lineBuf, n, nullptr);',
        '}',
        'int ScalerSlice::createLines(int size, int width)',
        '{',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scaler.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scaler.cpp': valid_text().replace('std::fill_n(m_plane[i].lineBuf, n, nullptr);', '', 1)})
        expect_fail(run_checker(root), 'missing scaler slice lineBuf init guardrail: std::fill_n(m_plane[i].lineBuf, n, nullptr);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/scaler.cpp': valid_text().replace(
            '    if (!m_plane[i].lineBuf)\n        return -1;\n    std::fill_n(m_plane[i].lineBuf, n, nullptr);\n',
            '    std::fill_n(m_plane[i].lineBuf, n, nullptr);\n    if (!m_plane[i].lineBuf)\n        return -1;\n',
            1,
        )})
        expect_fail(run_checker(root), 'ScalerSlice::create must clear lineBuf pointer slots after allocation so partial createLines() failures can destroy safely')

    print('ScalerSlice lineBuf init guard tests passed')


if __name__ == '__main__':
    main()
