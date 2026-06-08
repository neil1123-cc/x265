#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


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


def check_function(func_text, label, log_snippet, required_snippet):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    branch = 'if (!param || !analysis)'
    ret = 'return;'
    for snippet in (branch, log_snippet, ret, required_snippet):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} null guardrail: {snippet}'))

    branch_pos = func_text.find(branch)
    log_pos = func_text.find(log_snippet, branch_pos if branch_pos != -1 else 0)
    ret_pos = func_text.find(ret, log_pos if log_pos != -1 else 0)
    req_pos = func_text.find(required_snippet, ret_pos if ret_pos != -1 else 0)
    if -1 in (branch_pos, log_pos, ret_pos, req_pos) or not (branch_pos < log_pos < ret_pos < req_pos):
        failures.append((TARGET.as_posix(), 0, f'{label} must guard null param/analysis before dereferencing analysis state'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    alloc_text = extract_braced_block(text, 'void x265_alloc_analysis_data(x265_param *param, x265_analysis_data* analysis)')
    free_text = extract_braced_block(text, 'void x265_free_analysis_data(x265_param *param, x265_analysis_data* analysis)')

    failures = []
    failures.extend(check_function(
        alloc_text,
        'x265_alloc_analysis_data',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_alloc_analysis_data requires non-null param and analysis data\\n");',
        'x265_analysis_inter_data *interData = analysis->interData = nullptr;',
    ))
    failures.extend(check_function(
        free_text,
        'x265_free_analysis_data',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_free_analysis_data requires non-null param and analysis data\\n");',
        'int maxReuseLevel = X265_MAX(param->analysisSaveReuseLevel, param->analysisLoadReuseLevel);',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265 analysis data API null guards')
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

    print('x265 analysis data API null guards validated')


if __name__ == '__main__':
    main()
