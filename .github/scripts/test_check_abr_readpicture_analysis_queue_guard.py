#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_readpicture_analysis_queue_guard.py')


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
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'int analysisQId = m_cliopt.refId;',
                    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int written = analysisWrite * analysisPass->m_cliopt.numRefs;',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    'int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;',
                    'analysisIdx = analysisRead % m_parent->m_queueSize;',
                    'resultData = &m_parent->m_analysisBuffer[analysisQId][analysisIdx];',
                    'int slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].get();',
                    'while (m_threadActive.load() && resultData->poc == (uint32_t)ipread && !slotWrite)',
                    '{',
                    '    slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].waitForChange(slotWrite);',
                    '}',
                    'int write = slotWrite * analysisPass->m_cliopt.numRefs;',
                    'int read = m_parent->m_analysisRead[analysisQId][analysisIdx].get();',
                    'if ((resultData->poc != (uint32_t)ipread) || (read >= write))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Mismatched no-lookahead analysis slot for frame %d at slot %d encoder %u\\n", ipread, analysisIdx, m_id);',
                    '    m_ret = 4;',
                    '    return false;',
                    '}',
                    'readPos = resultData->poc % m_parent->m_queueSize;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'int analysisQId = m_cliopt.refId;\n'})
        expect_fail(run_checker(root), 'missing ABR readPicture analysis queue guardrail: PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'int analysisQId = m_cliopt.refId;',
                    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'int analysisQId = m_cliopt.refId;',
                    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int written = analysisWrite * analysisPass->m_cliopt.numRefs;',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    'int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::loadAnalysisData must guard analysis queue state before dereferencing it')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'int analysisQId = m_cliopt.refId;',
                    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int written = analysisWrite * analysisPass->m_cliopt.numRefs;',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    'int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;',
                    'analysisIdx = analysisRead % m_parent->m_queueSize;',
                    'resultData = &m_parent->m_analysisBuffer[analysisQId][analysisIdx];',
                    'readPos = resultData->poc % m_parent->m_queueSize;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::loadAnalysisData must validate no-lookahead slot identity before reusing readPos')

    print('ABR readPicture analysis queue guard tests passed')


if __name__ == '__main__':
    main()
