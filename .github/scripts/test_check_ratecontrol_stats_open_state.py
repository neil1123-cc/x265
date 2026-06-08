#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_stats_open_state.py')

# Coverage probe used by the scan for ratecontrol stats open-state guardrails.
NORMALIZED_PROBES = (
    'missing ratecontrol stats open-state guardrail: ',
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
                    'm_cutreeStatFileIn = x265_fopen(tmpFile, "rb");',
                    'else if (ferror(m_cutreeStatFileIn))',
                    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
                    'if (fclose(m_cutreeStatFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s.cutree\\" after open failure\\n", fileName);',
                    'm_cutreeStatFileIn = nullptr;',
                    'm_statFileOut = x265_fopen(statFileTmpname, "wb");',
                    'else if (ferror(m_statFileOut))',
                    'bool closeFailed = ferror(m_statFileOut) != 0;',
                    'if (fclose(m_statFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close output stats file \\"%s.temp\\" after open failure\\n", fileName);',
                    'm_statFileOut = nullptr;',
                    'm_cutreeStatFileOut = x265_fopen(statFileTmpname, "wb");',
                    'else if (ferror(m_cutreeStatFileOut))',
                    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
                    'if (fclose(m_cutreeStatFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree output stats file \\"%s.cutree.temp\\" after open failure\\n", fileName);',
                    'm_cutreeStatFileOut = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': 'm_statFileOut = x265_fopen(statFileTmpname, "wb");\nif (!m_statFileOut)\n    return false;\n',
            },
        )
        expect_fail(run_checker(root), 'missing ratecontrol stats open-state guardrail')

    print('Ratecontrol stats open-state guard tests passed')


if __name__ == '__main__':
    main()
