#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_cliopt.loadLevel && picInput)',
    'if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||',
    '!m_parent->m_analysisReadCnt)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\\n", m_id);',
    'goto fail;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread analysis-read guardrail: {snippet}'))

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

    thread_main_text = extract_braced_block('void PassEncoder::threadMain()')

    branch_pos = thread_main_text.find('if (m_cliopt.loadLevel && picInput)')
    guard_pos = thread_main_text.find('if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||', branch_pos if branch_pos != -1 else 0)
    cnt_guard_pos = thread_main_text.find('!m_parent->m_analysisReadCnt)', guard_pos if guard_pos != -1 else 0)
    read_pos = thread_main_text.find('m_parent->m_analysisReadCnt[m_cliopt.refId].incr();', guard_pos if guard_pos != -1 else 0)
    slot_pos = thread_main_text.find('m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();', read_pos if read_pos != -1 else 0)
    if -1 in (branch_pos, guard_pos, cnt_guard_pos, read_pos, slot_pos) or not (branch_pos < guard_pos < cnt_guard_pos < read_pos < slot_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard analysis-read state before incrementing it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain analysis-read guard')
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

    print('ABR thread analysis-read guard validated')


if __name__ == '__main__':
    main()
