#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_copyinfo_analysis_buffer_guard.py')


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
                'source/abrEncApp.cpp': '\n'.join((
                    'void PassEncoder::copyInfo(x265_analysis_data * src)',
                    '{',
                    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    'x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];',
                    'if (!prepareAnalysisCopySlot(index, src, m_analysisInfo))',
                    '{',
                    '    return;',
                    '}',
                    'copyIntraAnalysis(m_analysisInfo, src)',
                    'copyInterAnalysis(m_analysisInfo, src)',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];\n'})
        expect_fail(run_checker(root), 'missing ABR copyInfo analysis buffer guardrail: if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'void PassEncoder::copyInfo(x265_analysis_data * src)',
                    '{',
                    'x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];',
                    'if (!prepareAnalysisCopySlot(index, src, m_analysisInfo))',
                    '{',
                    '    return;',
                    '}',
                    'copyIntraAnalysis(m_analysisInfo, src)',
                    'copyInterAnalysis(m_analysisInfo, src)',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::copyInfo must guard analysis queue slots before preparing and copying analysis data')

    print('ABR copyInfo analysis buffer guard tests passed')


if __name__ == '__main__':
    main()
