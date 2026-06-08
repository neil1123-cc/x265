#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'int index = selectAnalysisWriteIndex(written);',
    'if (m_ret)',
    'int PassEncoder::selectAnalysisWriteIndex(uint32_t written)',
    'while (!emptyIdxFound && overwrite)',
    'if (read == write)',
    'int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();',
    'm_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);',
    'if (!emptyIdxFound && overwrite)',
    'x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);',
    'if (m_cliopt.loadLevel && m_parent && m_parent->m_analysisReadCnt)',
    'm_parent->m_analysisReadCnt[m_cliopt.refId].poke();',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR analysis slot wait guardrail: {snippet}'))

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

    select_text = extract_braced_block('int PassEncoder::selectAnalysisWriteIndex(uint32_t written)')
    copy_info_text = extract_braced_block('void PassEncoder::copyInfo(x265_analysis_data * src)')
    thread_text = extract_braced_block('void PassEncoder::threadMain()')

    select_call_pos = copy_info_text.find('int index = selectAnalysisWriteIndex(written);')
    ret_guard_pos = copy_info_text.find('if (m_ret)', select_call_pos if select_call_pos != -1 else 0)
    slot_guard_pos = copy_info_text.find('if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])', ret_guard_pos if ret_guard_pos != -1 else 0)
    if -1 in (select_call_pos, ret_guard_pos, slot_guard_pos) or not (select_call_pos < ret_guard_pos < slot_guard_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInfo must stop immediately when selectAnalysisWriteIndex fails'))

    loop_pos = select_text.find('while (!emptyIdxFound && overwrite)')
    read_eq_pos = select_text.find('if (read == write)', loop_pos if loop_pos != -1 else 0)
    wait_guard_pos = select_text.find('if (!emptyIdxFound && m_threadActive.load())', read_eq_pos if read_eq_pos != -1 else 0)
    prev_pos = select_text.find('int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();', wait_guard_pos if wait_guard_pos != -1 else 0)
    wait_pos = select_text.find('m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);', prev_pos if prev_pos != -1 else 0)
    fail_pos = select_text.find('if (!emptyIdxFound && overwrite)', wait_pos if wait_pos != -1 else 0)
    log_pos = select_text.find('x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\\n", m_id);', fail_pos if fail_pos != -1 else 0)
    if -1 in (loop_pos, read_eq_pos, wait_guard_pos, prev_pos, wait_pos, fail_pos, log_pos) or not (loop_pos < read_eq_pos < wait_guard_pos < prev_pos < wait_pos < fail_pos < log_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::selectAnalysisWriteIndex must block on analysisReadCnt progress instead of busy-spinning'))

    load_branch_pos = thread_text.find('if (m_cliopt.loadLevel && picInput)')
    read_incr_pos = thread_text.find('m_parent->m_analysisReadCnt[m_cliopt.refId].incr();', load_branch_pos if load_branch_pos != -1 else 0)
    fail_label_pos = thread_text.find('fail:', read_incr_pos if read_incr_pos != -1 else 0)
    poke_guard_pos = thread_text.find('if (m_cliopt.loadLevel && m_parent && m_parent->m_analysisReadCnt)', fail_label_pos if fail_label_pos != -1 else 0)
    poke_pos = thread_text.find('m_parent->m_analysisReadCnt[m_cliopt.refId].poke();', poke_guard_pos if poke_guard_pos != -1 else 0)
    if -1 in (load_branch_pos, read_incr_pos, fail_label_pos, poke_guard_pos, poke_pos) or not (load_branch_pos < read_incr_pos < fail_label_pos < poke_guard_pos < poke_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must poke analysisReadCnt on teardown so waiting writers can wake up'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR analysis slot wait guards')
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

    print('ABR analysis slot wait guards validated')


if __name__ == '__main__':
    main()
