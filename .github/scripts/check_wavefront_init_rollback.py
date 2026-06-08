#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET_CPP = Path('source/common/wavefront.cpp')
TARGET_H = Path('source/common/wavefront.h')
REQUIRED_CPP_SNIPPETS = (
    'void WaveFront::releaseState()',
    'releaseState();',
    'std::atomic<uint32_t>* internalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];',
    'std::atomic<uint32_t>* externalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];',
    'uint32_t* rowToIdx = X265_MALLOC(uint32_t, m_numRows);',
    'uint32_t* idxToRow = X265_MALLOC(uint32_t, m_numRows);',
    'if (!internalDependencyBitmap || !externalDependencyBitmap || !rowToIdx || !idxToRow)',
    'delete[] internalDependencyBitmap;',
    'delete[] externalDependencyBitmap;',
    'x265_free((void*)rowToIdx);',
    'x265_free((void*)idxToRow);',
    'm_row_to_idx = nullptr;',
    'm_idx_to_row = nullptr;',
    'm_internalDependencyBitmap = nullptr;',
    'm_externalDependencyBitmap = nullptr;',
    'return true;',
)
FORBIDDEN_CPP_SNIPPETS = (
    'return m_internalDependencyBitmap && m_externalDependencyBitmap;',
    'm_row_to_idx = X265_MALLOC(uint32_t, m_numRows);\n    m_idx_to_row = X265_MALLOC(uint32_t, m_numRows);\n\n    return m_internalDependencyBitmap && m_externalDependencyBitmap;',
)
REQUIRED_H_SNIPPETS = (
    'void releaseState();',
    ', m_numWords(0)',
    ', m_numRows(0)',
    ', m_sLayerId(0)',
    ', m_row_to_idx(nullptr)',
    ', m_idx_to_row(nullptr)',
)


def check_file(path, required, forbidden, label):
    if not path.is_file():
        return [(path.as_posix(), 0, f'missing {label} file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in forbidden:
        if snippet in text:
            failures.append((path.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
    for snippet in required:
        if snippet not in text:
            failures.append((path.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    failures.extend(check_file(repo_root / TARGET_CPP, REQUIRED_CPP_SNIPPETS, FORBIDDEN_CPP_SNIPPETS, 'WaveFront init rollback'))
    failures.extend(check_file(repo_root / TARGET_H, REQUIRED_H_SNIPPETS, (), 'WaveFront init rollback header'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check WaveFront init rollback guardrails')
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

    print('WaveFront init rollback validated')


if __name__ == '__main__':
    main()
