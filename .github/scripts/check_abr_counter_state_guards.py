#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)',
    'if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);',
    'int ipread = m_parent->m_picReadCnt[m_id].get();',
    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
    '!m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
    '!m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
    'if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);',
    'm_parent->m_picIdxReadCnt[m_id][idx].incr();',
    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
    '!m_parent->m_analysisReadCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
    'm_parent->m_analysisReadCnt[m_cliopt.refId].incr();',
    'm_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR counter-state guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
        brace_start = text.find('{', start)
        if brace_start == -1:
            return text[start:]
        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return text[start:]

    load_analysis_text = extract_braced_block('bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)')
    read_picture_text = extract_braced_block('bool PassEncoder::readPicture(x265_picture* dstPic, int view)')
    thread_main_text = extract_braced_block('void PassEncoder::threadMain()')

    read_guard_pos = read_picture_text.find('if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)')
    read_log_pos = read_picture_text.find('x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\\n", m_id);', read_guard_pos if read_guard_pos != -1 else 0)
    ipread_pos = read_picture_text.find('int ipread = m_parent->m_picReadCnt[m_id].get();', read_log_pos if read_log_pos != -1 else 0)
    if -1 in (read_guard_pos, read_log_pos, ipread_pos) or not (read_guard_pos < read_log_pos < ipread_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::readPicture must guard picture counters before reading ipread'))

    analysis_guard_pos = load_analysis_text.find('if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||')
    analysis_log_pos = load_analysis_text.find('x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);', analysis_guard_pos if analysis_guard_pos != -1 else 0)
    analysis_write_pos = load_analysis_text.find('int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();', analysis_log_pos if analysis_log_pos != -1 else 0)
    analysis_read_pos = load_analysis_text.find('int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();', analysis_write_pos if analysis_write_pos != -1 else 0)
    if -1 in (analysis_guard_pos, analysis_log_pos, analysis_write_pos, analysis_read_pos) or not (analysis_guard_pos < analysis_log_pos < analysis_write_pos < analysis_read_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::loadAnalysisData must guard analysis queue state before reading analysis counters'))

    queue_guard_pos = thread_main_text.find('if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)')
    queue_log_pos = thread_main_text.find('x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\\n", m_id);', queue_guard_pos if queue_guard_pos != -1 else 0)
    queue_incr_pos = thread_main_text.find('m_parent->m_picIdxReadCnt[m_id][idx].incr();', queue_log_pos if queue_log_pos != -1 else 0)
    if -1 in (queue_guard_pos, queue_log_pos, queue_incr_pos) or not (queue_guard_pos < queue_log_pos < queue_incr_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard queue counters before incrementing them'))

    analysis_read_guard_pos = thread_main_text.find('if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||', queue_incr_pos if queue_incr_pos != -1 else 0)
    analysis_read_log_pos = thread_main_text.find('x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);', analysis_read_guard_pos if analysis_read_guard_pos != -1 else 0)
    analysis_read_cnt_incr_pos = thread_main_text.find('m_parent->m_analysisReadCnt[m_cliopt.refId].incr();', analysis_read_log_pos if analysis_read_log_pos != -1 else 0)
    analysis_read_slot_incr_pos = thread_main_text.find('m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();', analysis_read_cnt_incr_pos if analysis_read_cnt_incr_pos != -1 else 0)
    if -1 in (analysis_read_guard_pos, analysis_read_log_pos, analysis_read_cnt_incr_pos, analysis_read_slot_incr_pos) or not (analysis_read_guard_pos < analysis_read_log_pos < analysis_read_cnt_incr_pos < analysis_read_slot_incr_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard analysis read state before incrementing analysis counters'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR counter-state guards')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('ABR counter-state guards validated')


if __name__ == '__main__':
    main()
