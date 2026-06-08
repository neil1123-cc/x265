#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_motion_sea_scratch_guard.py')


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
        'int MotionEstimate::motionEstimate(...)',
        '{',
        '    switch (search)',
        '    {',
        '    case X265_SEA:',
        '    {',
        '        int16_t* meScratchBuffer = nullptr;',
        '        int scratchSize = merange * 2 + 4;',
        '        if (scratchSize)',
        '        {',
        '            meScratchBuffer = X265_MALLOC(int16_t, scratchSize);',
        '            if (!meScratchBuffer)',
        '                break;',
        '            std::fill_n(meScratchBuffer, scratchSize, int16_t(0));',
        '        }',
        '        break;',
        '    }',
        '    case X265_FULL_SEARCH:',
        '        break;',
        '    }',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/motion.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/motion.cpp': valid_text().replace('if (!meScratchBuffer)\n                break;\n', '', 1)})
        expect_fail(run_checker(root), 'missing SEA scratch guardrail: if (!meScratchBuffer)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/motion.cpp': valid_text().replace(
            '            if (!meScratchBuffer)\n                break;\n            std::fill_n(meScratchBuffer, scratchSize, int16_t(0));\n',
            '            std::fill_n(meScratchBuffer, scratchSize, int16_t(0));\n            if (!meScratchBuffer)\n                break;\n',
            1,
        )})
        expect_fail(run_checker(root), 'SEA scratch buffer must be null-checked before zero-fill')

    print('SEA motion scratch guard tests passed')


if __name__ == '__main__':
    main()
