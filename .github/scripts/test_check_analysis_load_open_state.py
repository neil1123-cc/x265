#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_load_open_state.py')

# Coverage probes used by the scan for analysis-load open-state guardrails.
NORMALIZED_PROBES = (
    'forbidden analysis load open-state short-circuit close regression: ',
    'missing analysis load open-state guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis load file \\"%s\\" after open failure\\n", m_param->analysisLoad);',
                    'm_analysisFileIn = nullptr;',
                    'int rightOffset, bottomOffset;',
                    'if (fread(&rightOffset, sizeof(int), 1, m_analysisFileIn) != 1)',
                    '    return;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");\nif (!m_analysisFileIn)\n    return;\n',
            },
        )
        expect_fail(run_checker(root), 'missing analysis load open-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis load file \\"%s\\" after open failure\\n", m_param->analysisLoad);',
                    'm_analysisFileIn = nullptr;',
                    'int rightOffset, bottomOffset;',
                    'if (fread(&rightOffset, sizeof(int), 1, m_analysisFileIn) != 1)',
                    '    return;',
                    'if (std::ferror(m_analysisFileIn) || std::fclose(m_analysisFileIn))',
                    '    m_aborted = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden analysis load open-state short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_analysisFileIn = x265_fopen(m_param->analysisLoad, "rb");',
                    'int rightOffset, bottomOffset;',
                    'if (fread(&rightOffset, sizeof(int), 1, m_analysisFileIn) != 1)',
                    '    return;',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis load file \\"%s\\" after open failure\\n", m_param->analysisLoad);',
                    'm_analysisFileIn = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'analysis load open-failure close guard must stay before the analysis-read path')

    print('Analysis load open-state guard tests passed')


if __name__ == '__main__':
    main()
