#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||',
    '!m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||',
    '!m_parentEnc->m_parent->m_picIdxReadCnt[srcId] ||',
    '!m_parentEnc->m_parent->m_inputPicBuffer || !m_parentEnc->m_parent->m_inputPicBuffer[m_id] ||',
    '!m_parentEnc->m_parent->m_inputPicBuffer[srcId])',
    'x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\\n", m_id);',
    'x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\\n", m_id);',
    'if (!m_input[view])',
    'x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader input state for view %d\\n", view);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread queue-state guardrail: {snippet}'))

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

    scaler_text = extract_braced_block('void Scaler::threadMain()')
    reader_text = extract_braced_block('void Reader::threadMain()')

    scaler_guard_pos = scaler_text.find('if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||')
    scaler_log_pos = scaler_text.find('x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\\n", m_id);', scaler_guard_pos if scaler_guard_pos != -1 else 0)
    scaler_qdepth_pos = scaler_text.find('int QDepth = m_parentEnc->m_parent->m_queueSize;', scaler_log_pos if scaler_log_pos != -1 else 0)
    if -1 in (scaler_guard_pos, scaler_log_pos, scaler_qdepth_pos) or not (scaler_guard_pos < scaler_log_pos < scaler_qdepth_pos):
        failures.append((TARGET.as_posix(), 0, 'Scaler::threadMain must guard queue state before reading QDepth'))

    reader_guard_pos = reader_text.find('if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||')
    reader_log_pos = reader_text.find('x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\\n", m_id);', reader_guard_pos if reader_guard_pos != -1 else 0)
    reader_qdepth_pos = reader_text.find('int QDepth = m_parentEnc->m_parent->m_queueSize;', reader_log_pos if reader_log_pos != -1 else 0)
    if -1 in (reader_guard_pos, reader_log_pos, reader_qdepth_pos) or not (reader_guard_pos < reader_log_pos < reader_qdepth_pos):
        failures.append((TARGET.as_posix(), 0, 'Reader::threadMain must guard queue state before reading QDepth'))

    input_guard_pos = reader_text.find('if (!m_input[view])', reader_qdepth_pos if reader_qdepth_pos != -1 else 0)
    read_pos = reader_text.find('if (m_input[view]->readPicture(*src))', input_guard_pos if input_guard_pos != -1 else 0)
    if -1 in (input_guard_pos, read_pos) or not (input_guard_pos < read_pos):
        failures.append((TARGET.as_posix(), 0, 'Reader::threadMain must guard m_input[view] before readPicture(*src)'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread queue-state guards')
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

    print('ABR thread queue-state guards validated')


if __name__ == '__main__':
    main()
