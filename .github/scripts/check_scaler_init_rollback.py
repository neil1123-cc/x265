#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET_CPP = Path('source/common/scaler.cpp')
TARGET_H = Path('source/common/scaler.h')

CPP_REQUIRED_SNIPPETS = (
    'void ScalerFilterManager::resetState()',
    'delete m_slices[i];',
    'delete m_ScalerFilters[i];',
    'resetState();\n        return -1;',
    'if (initScalerSlice() < 0)\n    {\n        resetState();\n        return -1;\n    }',
    'm_slices[i] = new (std::nothrow) ScalerSlice;',
    'if (!m_slices[i])\n        {\n            x265_log(nullptr, X265_LOG_ERROR, "alloc_slice m_slice[%d] failed\\n", i);\n            resetState();\n            return -1;\n        }',
)
H_REQUIRED_SNIPPETS = (
    '~ScalerSlice() { destroy(); }',
    'void resetState();',
    '~ScalerFilterManager() {',
    'resetState();',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    cpp_path = repo_root / TARGET_CPP
    if not cpp_path.is_file():
        failures.append((TARGET_CPP.as_posix(), 0, 'missing file'))
    else:
        text = cpp_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in CPP_REQUIRED_SNIPPETS:
            if snippet not in text:
                failures.append((TARGET_CPP.as_posix(), 0, f'missing scaler init rollback guardrail: {snippet}'))
        if 'm_slices[i] = new ScalerSlice;' in text:
            failures.append((TARGET_CPP.as_posix(), 0, 'forbidden scaler init rollback regression: m_slices[i] = new ScalerSlice;'))

    h_path = repo_root / TARGET_H
    if not h_path.is_file():
        failures.append((TARGET_H.as_posix(), 0, 'missing file'))
    else:
        text = h_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in H_REQUIRED_SNIPPETS:
            if snippet not in text:
                failures.append((TARGET_H.as_posix(), 0, f'missing scaler init rollback guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaler init rollback guardrails')
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

    print('Scaler init rollback validated')


if __name__ == '__main__':
    main()
