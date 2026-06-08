#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'void PassEncoder::copyInfo(x265_analysis_data * src)',
    'if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue slot for encoder %u\\n", m_id);',
    'x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];',
    'if (!prepareAnalysisCopySlot(index, src, m_analysisInfo))',
    'copyIntraAnalysis(m_analysisInfo, src)',
    'copyInterAnalysis(m_analysisInfo, src)',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR copyInfo analysis buffer guardrail: {snippet}'))

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

    copy_info_text = extract_braced_block('void PassEncoder::copyInfo(x265_analysis_data * src)')

    slot_guard_pos = copy_info_text.find('if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])')
    info_pos = copy_info_text.find('x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];', slot_guard_pos if slot_guard_pos != -1 else 0)
    prepare_pos = copy_info_text.find('if (!prepareAnalysisCopySlot(index, src, m_analysisInfo))', info_pos if info_pos != -1 else 0)
    intra_copy_pos = copy_info_text.find('copyIntraAnalysis(m_analysisInfo, src)', prepare_pos if prepare_pos != -1 else 0)
    inter_copy_pos = copy_info_text.find('copyInterAnalysis(m_analysisInfo, src)', prepare_pos if prepare_pos != -1 else 0)
    if -1 in (slot_guard_pos, info_pos, prepare_pos, intra_copy_pos, inter_copy_pos) or not (slot_guard_pos < info_pos < prepare_pos < intra_copy_pos and prepare_pos < inter_copy_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInfo must guard analysis queue slots before preparing and copying analysis data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::copyInfo analysis buffer guards')
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

    print('ABR copyInfo analysis buffer guards validated')


if __name__ == '__main__':
    main()
