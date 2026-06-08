#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_open_state.py')

# Coverage probes used by the scan for analysis open-state guardrails.
NORMALIZED_PROBES = (
    'expected both analysis output open-failure paths to be guarded',
    'expected two guarded analysis output open-failure branches',
    'expected two guarded analysis output fclose calls',
    'expected analysis output handles to be cleared in both open-failure paths',
    'forbidden analysis open-state short-circuit close regression: ',
    'missing analysis open-state guardrail: ',
    'analysis open-state guards must preserve the save-output path before the multi-pass output and input paths',
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
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis save file \\"%s.temp\\" after open failure\\n", m_param->analysisSave);',
                    'm_analysisFileOut = nullptr;',
                    'if (m_param->analysisMultiPassRefine || m_param->analysisMultiPassDistortion)',
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis 2 pass file \\"%s.temp\\" after open failure\\n", name);',
                    'm_analysisFileOut = nullptr;',
                    'm_analysisFileIn = x265_fopen(name, "rb");',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\" after open failure\\n", name);',
                    'm_analysisFileIn = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_analysisFileOut = x265_fopen(temp, "wb");\nif (!m_analysisFileOut)\n    return;\n',
            },
        )
        expect_fail(run_checker(root), 'missing analysis open-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis save file \\"%s.temp\\" after open failure\\n", m_param->analysisSave);',
                    'm_analysisFileOut = nullptr;',
                    'if (m_param->analysisMultiPassRefine || m_param->analysisMultiPassDistortion)',
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis 2 pass file \\"%s.temp\\" after open failure\\n", name);',
                    'm_analysisFileOut = nullptr;',
                    'm_analysisFileIn = x265_fopen(name, "rb");',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\" after open failure\\n", name);',
                    'm_analysisFileIn = nullptr;',
                    'if (std::ferror(m_analysisFileOut) || std::fclose(m_analysisFileOut))',
                    '    m_aborted = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden analysis open-state short-circuit close regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    'bool closeFailed = std::ferror(m_analysisFileOut) != 0;',
                    'if (std::fclose(m_analysisFileOut))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis save file \\"%s.temp\\" after open failure\\n", m_param->analysisSave);',
                    'm_analysisFileOut = nullptr;',
                    'if (m_param->analysisMultiPassRefine || m_param->analysisMultiPassDistortion)',
                    'm_analysisFileOut = x265_fopen(temp, "wb");',
                    'else if (std::ferror(m_analysisFileOut))',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis 2 pass file \\"%s.temp\\" after open failure\\n", name);',
                    'm_analysisFileOut = nullptr;',
                    'm_analysisFileIn = x265_fopen(name, "rb");',
                    'else if (std::ferror(m_analysisFileIn))',
                    'bool closeFailed = std::ferror(m_analysisFileIn) != 0;',
                    'if (std::fclose(m_analysisFileIn))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "failed to close analysis input file \\"%s\\" after open failure\\n", name);',
                    'm_analysisFileIn = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected guarded analysis output close handling for both open-failure paths')

    print('Analysis open-state guard tests passed')


if __name__ == '__main__':
    main()
