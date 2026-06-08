#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_cutree_read_fail_state.py')

# Coverage probes used by the scan for ratecontrol cutree read-failure guards.
NORMALIZED_PROBES = (
    'ratecontrol cutree file reads must guard missing input state and retire the stream on read failure',
    'ratecontrol cutree file reads must distinguish read errors from incomplete stats data',
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
                    'auto failCutreeRead = [this]()',
                    '{',
                    '    if (m_cutreeStatFileIn)',
                    '    {',
                    '        const char* fileName = m_param->rc.statFileName;',
                    '        char* cutreeFileName = strcatFilename(fileName, ".cutree");',
                    '        bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
                    '        if (fclose(m_cutreeStatFileIn))',
                    '            closeFailed = true;',
                    '        x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s\\" after read failure\\n", cutreeFileName ? cutreeFileName : fileName);',
                    '        m_cutreeStatFileIn = nullptr;',
                    '    }',
                    '};',
                    'if (!m_cutreeStatFileIn)',
                    '    goto readError;',
                    'if (X265_SHARE_MODE_FILE == m_param->rc.dataShareMode && m_cutreeStatFileIn && ferror(m_cutreeStatFileIn))',
                    '    goto readError;',
                    'x265_log(m_param, X265_LOG_ERROR, "Incomplete CU-tree stats file.\\n");',
                    'failCutreeRead();',
                    'readError:',
                    'x265_log(m_param, X265_LOG_ERROR, "CU-tree stats file read failure.\\n");',
                    'failCutreeRead();',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/ratecontrol.cpp': 'goto fail;\n'})
        expect_fail(run_checker(root), 'missing ratecontrol cutree read fail-state guardrail: auto failCutreeRead = [this]()')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'auto failCutreeRead = [this]()',
                    '{',
                    '    if (m_cutreeStatFileIn)',
                    '    {',
                    '        m_cutreeStatFileIn = nullptr;',
                    '        if (fclose(m_cutreeStatFileIn))',
                    '            return;',
                    '    }',
                    '};',
                    'if (!m_cutreeStatFileIn)',
                    '    goto readError;',
                    'readError:',
                    'x265_log(m_param, X265_LOG_ERROR, "CU-tree stats file read failure.\\n");',
                    'failCutreeRead();',
                    'x265_log(m_param, X265_LOG_ERROR, "Incomplete CU-tree stats file.\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ratecontrol cutree read fail-state helper must close the stream before clearing the member pointer')

    print('Ratecontrol cutree read fail-state guard tests passed')


if __name__ == '__main__':
    main()
