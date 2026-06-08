#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_create_rowstate_alloc_guards.py')

# Coverage probe used by the scan for row-state staging guardrails.
NORMALIZED_PROBES = (
    'Frame::create must fully stage row-state allocations before assigning member state',
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


def valid_text():
    return '\n'.join((
        'bool Frame::create(x265_param *param, float* quantOffsets)',
        '{',
        '    ThreadSafeInteger* stagedReconRowFlag = new (std::nothrow) ThreadSafeInteger[m_numRows];',
        '    ThreadSafeInteger* stagedReconColCount = new (std::nothrow) ThreadSafeInteger[m_numRows];',
        '    ThreadSafeInteger* stagedCtuMEFlags = new (std::nothrow) ThreadSafeInteger[m_numRows * m_numCols];',
        '    float* stagedQuantOffsets = nullptr;',
        '    stagedQuantOffsets = new (std::nothrow) float[cuCount];',
        '    if (!stagedReconRowFlag || !stagedReconColCount || !stagedCtuMEFlags || (quantOffsets && !stagedQuantOffsets))',
        '    {',
        '        delete[] stagedReconRowFlag;',
        '        delete[] stagedReconColCount;',
        '        delete[] stagedCtuMEFlags;',
        '        delete[] stagedQuantOffsets;',
        '        return false;',
        '    }',
        '    m_reconRowFlag = stagedReconRowFlag;',
        '    m_reconColCount = stagedReconColCount;',
        '    m_ctuMEFlags = stagedCtuMEFlags;',
        '    m_quantOffsets = stagedQuantOffsets;',
        '    return true;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('ThreadSafeInteger* stagedReconRowFlag = new (std::nothrow) ThreadSafeInteger[m_numRows];', 'm_reconRowFlag = new ThreadSafeInteger[m_numRows];', 1)})
        expect_fail(run_checker(root), 'forbidden frame create row-state allocation regression: m_reconRowFlag = new ThreadSafeInteger[m_numRows];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/frame.cpp': valid_text().replace('        delete[] stagedQuantOffsets;\n', '', 1)})
        expect_fail(run_checker(root), 'missing frame create row-state allocation guardrail: delete[] stagedQuantOffsets;')

    print('Frame::create row-state allocation guard tests passed')


if __name__ == '__main__':
    main()
