#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/frame.cpp')
SIGNATURE = 'bool Frame::create(x265_param *param, float* quantOffsets)'


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
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


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing Frame::create function')]

    failures = []
    required = (
        'ThreadSafeInteger* stagedReconRowFlag = new (std::nothrow) ThreadSafeInteger[m_numRows];',
        'ThreadSafeInteger* stagedReconColCount = new (std::nothrow) ThreadSafeInteger[m_numRows];',
        'ThreadSafeInteger* stagedCtuMEFlags = new (std::nothrow) ThreadSafeInteger[m_numRows * m_numCols];',
        'float* stagedQuantOffsets = nullptr;',
        'stagedQuantOffsets = new (std::nothrow) float[cuCount];',
        'if (!stagedReconRowFlag || !stagedReconColCount || !stagedCtuMEFlags || (quantOffsets && !stagedQuantOffsets))',
        'delete[] stagedReconRowFlag;',
        'delete[] stagedReconColCount;',
        'delete[] stagedCtuMEFlags;',
        'delete[] stagedQuantOffsets;',
        'm_reconRowFlag = stagedReconRowFlag;',
        'm_reconColCount = stagedReconColCount;',
        'm_ctuMEFlags = stagedCtuMEFlags;',
        'm_quantOffsets = stagedQuantOffsets;',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing frame create row-state allocation guardrail: {snippet}'))

    forbidden = (
        'm_reconRowFlag = new ThreadSafeInteger[m_numRows];',
        'm_reconColCount = new ThreadSafeInteger[m_numRows];',
        'm_ctuMEFlags = new ThreadSafeInteger[m_numRows * m_numCols];',
        'm_quantOffsets = new float[cuCount];',
    )
    for snippet in forbidden:
        if snippet in func_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden frame create row-state allocation regression: {snippet}'))

    alloc_row_pos = func_text.find('ThreadSafeInteger* stagedReconRowFlag = new (std::nothrow) ThreadSafeInteger[m_numRows];')
    alloc_quant_pos = func_text.find('stagedQuantOffsets = new (std::nothrow) float[cuCount];', alloc_row_pos if alloc_row_pos != -1 else 0)
    assign_row_pos = func_text.find('m_reconRowFlag = stagedReconRowFlag;', alloc_quant_pos if alloc_quant_pos != -1 else 0)
    assign_quant_pos = func_text.find('m_quantOffsets = stagedQuantOffsets;', assign_row_pos if assign_row_pos != -1 else 0)
    if -1 in (alloc_row_pos, alloc_quant_pos, assign_row_pos, assign_quant_pos) or not (alloc_row_pos < alloc_quant_pos < assign_row_pos < assign_quant_pos):
        failures.append((TARGET.as_posix(), 0, 'Frame::create must fully stage row-state allocations before assigning member state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Frame::create row-state allocation guards')
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

    print('Frame::create row-state allocation guards validated')


if __name__ == '__main__':
    main()
