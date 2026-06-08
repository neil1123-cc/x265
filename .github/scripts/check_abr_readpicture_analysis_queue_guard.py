#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'int analysisQId = m_cliopt.refId;',
    'PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];',
    'if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||',
    '!m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||',
    '!m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||',
    '!m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);',
    'int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();',
    'int written = analysisWrite * analysisPass->m_cliopt.numRefs;',
    'int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();',
    'int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;',
    'analysisIdx = analysisRead % m_parent->m_queueSize;',
    'int slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].get();',
    'while (m_threadActive.load() && resultData->poc == (uint32_t)ipread && !slotWrite)',
    'slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].waitForChange(slotWrite);',
    'int write = slotWrite * analysisPass->m_cliopt.numRefs;',
    'int read = m_parent->m_analysisRead[analysisQId][analysisIdx].get();',
    'if ((resultData->poc != (uint32_t)ipread) || (read >= write))',
    'x265_log(m_param, X265_LOG_ERROR, "Mismatched no-lookahead analysis slot for frame %d at slot %d encoder %u\\n",',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR readPicture analysis queue guardrail: {snippet}'))

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

    qid_pos = load_analysis_text.find('int analysisQId = m_cliopt.refId;')
    pass_pos = load_analysis_text.find('PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];', qid_pos if qid_pos != -1 else 0)
    guard_pos = load_analysis_text.find('if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||', pass_pos if pass_pos != -1 else 0)
    log_pos = load_analysis_text.find('x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\\n", m_id);', guard_pos if guard_pos != -1 else 0)
    analysis_write_pos = load_analysis_text.find('int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();', log_pos if log_pos != -1 else 0)
    written_pos = load_analysis_text.find('int written = analysisWrite * analysisPass->m_cliopt.numRefs;', analysis_write_pos if analysis_write_pos != -1 else 0)
    analysis_read_pos = load_analysis_text.find('int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();', written_pos if written_pos != -1 else 0)
    slot_write_pos = load_analysis_text.find('int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;', analysis_read_pos if analysis_read_pos != -1 else 0)
    if -1 in (qid_pos, pass_pos, guard_pos, log_pos, analysis_write_pos, written_pos, analysis_read_pos, slot_write_pos) or not (qid_pos < pass_pos < guard_pos < log_pos < analysis_write_pos < written_pos < analysis_read_pos < slot_write_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::loadAnalysisData must guard analysis queue state before dereferencing it'))

    no_lookahead_pos = load_analysis_text.find('analysisIdx = analysisRead % m_parent->m_queueSize;')
    result_pos = load_analysis_text.find('resultData = &m_parent->m_analysisBuffer[analysisQId][analysisIdx];', no_lookahead_pos if no_lookahead_pos != -1 else 0)
    slot_guard_pos = load_analysis_text.find('int slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].get();', result_pos if result_pos != -1 else 0)
    slot_wait_pos = load_analysis_text.find('while (m_threadActive.load() && resultData->poc == (uint32_t)ipread && !slotWrite)', slot_guard_pos if slot_guard_pos != -1 else 0)
    slot_read_pos = load_analysis_text.find('int read = m_parent->m_analysisRead[analysisQId][analysisIdx].get();', slot_wait_pos if slot_wait_pos != -1 else 0)
    mismatch_pos = load_analysis_text.find('if ((resultData->poc != (uint32_t)ipread) || (read >= write))', slot_read_pos if slot_read_pos != -1 else 0)
    read_pos_pos = load_analysis_text.find('readPos = resultData->poc % m_parent->m_queueSize;', mismatch_pos if mismatch_pos != -1 else 0)
    if -1 in (no_lookahead_pos, result_pos, slot_guard_pos, slot_wait_pos, slot_read_pos, mismatch_pos, read_pos_pos) or not (no_lookahead_pos < result_pos < slot_guard_pos < slot_wait_pos < slot_read_pos < mismatch_pos < read_pos_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::loadAnalysisData must validate no-lookahead slot identity before reusing readPos'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::loadAnalysisData analysis queue guards')
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

    print('ABR readPicture analysis queue guards validated')


if __name__ == '__main__':
    main()
