#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_picyuv_offset_rollback.py')


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
        'bool PicYuv::createOffsets(const SPS& sps)',
        '{',
        'fail:',
        '    X265_FREE(m_buOffsetC);',
        '    m_buOffsetC = nullptr;',
        '    X265_FREE(m_buOffsetY);',
        '    m_buOffsetY = nullptr;',
        '    X265_FREE(m_cuOffsetC);',
        '    m_cuOffsetC = nullptr;',
        '    X265_FREE(m_cuOffsetY);',
        '    m_cuOffsetY = nullptr;',
        '    return false;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/picyuv.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/picyuv.cpp': valid_text().replace('X265_FREE(m_cuOffsetY);', '', 1)})
        expect_fail(run_checker(root), 'missing PicYuv offset rollback guardrail: X265_FREE(m_cuOffsetY);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/picyuv.cpp': valid_text().replace('m_buOffsetY = nullptr;', 'return false;', 1)})
        expect_fail(run_checker(root), 'PicYuv::createOffsets must release all partially allocated offset tables before returning failure')

    print('PicYuv offset rollback guard tests passed')


if __name__ == '__main__':
    main()
