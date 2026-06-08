#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_counter_state_guards.py')


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
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
                    '}',
                    'int ipread = m_parent->m_picReadCnt[m_id].get();',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
                    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '    !m_parent->m_analysisReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '!m_parent->m_analysisReadCnt)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'int ipread = m_parent->m_picReadCnt[m_id].get();\n'})
        expect_fail(run_checker(root), 'missing ABR counter-state guardrail: if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    '}',
                    'void helper()',
                    '{',
                    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'int ipread = m_parent->m_picReadCnt[m_id].get();',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
                    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '    !m_parent->m_analysisReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '!m_parent->m_analysisReadCnt)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::readPicture must guard picture counters before reading ipread')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
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
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
                    '}',
                    'int ipread = m_parent->m_picReadCnt[m_id].get();',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
                    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '    !m_parent->m_analysisReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '!m_parent->m_analysisReadCnt)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::loadAnalysisData must guard analysis queue state before reading analysis counters')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
                    '}',
                    'int ipread = m_parent->m_picReadCnt[m_id].get();',
                    '}',
                    'void helper()',
                    '{',
                    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
                    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '    !m_parent->m_analysisReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '!m_parent->m_analysisReadCnt)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::threadMain must guard queue counters before incrementing them')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
                    '{',
                    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
                    '    !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
                    '    !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
                    '    !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
                    '}',
                    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
                    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
                    '}',
                    'bool PassEncoder::readPicture(x265_picture* dstPic, int view)',
                    '{',
                    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
                    '}',
                    'int ipread = m_parent->m_picReadCnt[m_id].get();',
                    '}',
                    'void helper()',
                    '{',
                    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
                    '    !m_parent->m_analysisReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'void PassEncoder::threadMain()',
                    '{',
                    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
                    '}',
                    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
                    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
                    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
                    '}',
                    '!m_parent->m_analysisReadCnt)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::threadMain must guard analysis read state before incrementing analysis counters')

    print('ABR counter-state guard tests passed')


if __name__ == '__main__':
    main()
