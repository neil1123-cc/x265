#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_write_fail_state.py')

# Coverage probe used by the scan for ratecontrol write-failure state guards.
NORMALIZED_PROBES = (
    'ratecontrol stats writes must guard entry state and retire both output streams on write failure',
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'auto failStatsWrite = [this](FILE*& file, const char* logName)',
                    '{',
                    '    if (file)',
                    '    {',
                    '        bool closeFailed = ferror(file) != 0;',
                    '        if (fclose(file))',
                    '            closeFailed = true;',
                    '        x265_log_file(m_param, X265_LOG_WARNING, "failed to close %s after write failure\\n", logName);',
                    '        file = nullptr;',
                    '    }',
                    '};',
                    'if (!m_statFileOut || (m_param->rc.cuTree && IS_REFERENCED(curFrame) && !m_param->rc.bStatRead && X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && !m_cutreeStatFileOut))',
                    '    goto writeFailure;',
                    'writeFailure:',
                    'failStatsWrite(m_statFileOut, "output stats file");',
                    'failStatsWrite(m_cutreeStatFileOut, "cutree output stats file");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/ratecontrol.cpp': 'goto writeFailure;\n'})
        expect_fail(run_checker(root), 'missing ratecontrol write fail-state guardrail: auto failStatsWrite = [this](FILE*& file, const char* logName)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'auto failStatsWrite = [this](FILE*& file, const char* logName)',
                    '{',
                    '    if (file)',
                    '    {',
                    '        bool closeFailed = ferror(file) != 0;',
                    '        file = nullptr;',
                    '        if (fclose(file))',
                    '            closeFailed = true;',
                    '    }',
                    '};',
                    'if (!m_statFileOut || (m_param->rc.cuTree && IS_REFERENCED(curFrame) && !m_param->rc.bStatRead && X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && !m_cutreeStatFileOut))',
                    '    goto writeFailure;',
                    'writeFailure:',
                    'failStatsWrite(m_statFileOut, "output stats file");',
                    'failStatsWrite(m_cutreeStatFileOut, "cutree output stats file");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ratecontrol write fail-state helper must close the stream before clearing the member pointer')

    print('Ratecontrol write fail-state guard tests passed')


if __name__ == '__main__':
    main()
