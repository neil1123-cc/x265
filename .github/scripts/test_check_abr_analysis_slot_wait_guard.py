#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_analysis_slot_wait_guard.py')

# Coverage probe used by the scan for the reviewed ABR analysis wait guard.
NORMALIZED_PROBES = (
    'PassEncoder::threadMain must poke analysisReadCnt on teardown so waiting writers can wake up',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'void PassEncoder::copyInfo(x265_analysis_data * src)',
                    '{',
                    'int index = selectAnalysisWriteIndex(written);',
                    'if (m_ret)',
                    '    return;',
                    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
                    '{',
                    '}',
                    '}',
                    'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)',
                    '{',
                    'while (!emptyIdxFound && overwrite)',
                    '{',
                    '    if (read == write)',
                    '    {',
                    '        break;',
                    '    }',
                    '    if (!emptyIdxFound && m_threadActive.load())',
                    '    {',
                    '        int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();',
                    '        m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);',
                    '    }',
                    '}',
                    'if (!emptyIdxFound && overwrite)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (m_cliopt.loadLevel && picInput)',
                    '{',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    '}',
                    'fail:',
                    'if (m_cliopt.loadLevel && m_parent && m_parent->m_analysisReadCnt)',
                    '{',
                    '    m_parent->m_analysisReadCnt[m_cliopt.refId].poke();',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)\n{\nwhile (!emptyIdxFound && overwrite)\n{\n}\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR analysis slot wait guardrail: int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'while (!emptyIdxFound && overwrite)',
                    '{',
                    '    if (read == write)',
                    '    {',
                    '        break;',
                    '    }',
                    '    if (!emptyIdxFound && m_threadActive.load())',
                    '    {',
                    '        int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();',
                    '        m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);',
                    '    }',
                    '}',
                    'if (!emptyIdxFound && overwrite)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)',
                    '{',
                    'while (!emptyIdxFound && overwrite)',
                    '{',
                    '    if (read == write)',
                    '    {',
                    '        break;',
                    '    }',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::selectAnalysisWriteIndex must block on analysisReadCnt progress instead of busy-spinning')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void PassEncoder::copyInfo(x265_analysis_data * src)',
                    '{',
                    'int index = selectAnalysisWriteIndex(written);',
                    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
                    '{',
                    '}',
                    '}',
                    'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)',
                    '{',
                    'while (!emptyIdxFound && overwrite)',
                    '{',
                    '    if (read == write)',
                    '    {',
                    '        break;',
                    '    }',
                    '    if (!emptyIdxFound && m_threadActive.load())',
                    '    {',
                    '        int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();',
                    '        m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);',
                    '    }',
                    '}',
                    'if (!emptyIdxFound && overwrite)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::copyInfo must stop immediately when selectAnalysisWriteIndex fails')

    print('ABR analysis slot wait guard tests passed')


if __name__ == '__main__':
    main()
