#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')


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


def check_function(func_text, label, guard_snippet, log_snippet, return_snippet, required_snippet, ordering_message):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    for snippet in (guard_snippet, log_snippet, return_snippet, required_snippet):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} null guardrail: {snippet}'))

    guard_pos = func_text.find(guard_snippet)
    log_pos = func_text.find(log_snippet, guard_pos if guard_pos != -1 else 0)
    return_pos = func_text.find(return_snippet, log_pos if log_pos != -1 else 0)
    required_pos = func_text.find(required_snippet, return_pos if return_pos != -1 else 0)
    if -1 in (guard_pos, log_pos, return_pos, required_pos) or not (guard_pos < log_pos < return_pos < required_pos):
        failures.append((TARGET.as_posix(), 0, ordering_message))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    check_params_text = extract_braced_block(text, 'int x265_check_params(x265_param* param)')
    fastfirstpass_text = extract_braced_block(text, 'void x265_param_apply_fastfirstpass(x265_param* param)')
    print_params_text = extract_braced_block(text, 'void x265_print_params(x265_param* param)')

    failures = []
    failures.extend(check_function(
        check_params_text,
        'x265_check_params',
        'if (!param)',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_check_params requires a non-null parameter struct\\n");',
        'return X265_PARAM_BAD_VALUE;',
        '#define CHECK(expr, msg) check_failed |= _confirm(param, expr, msg)',
        'x265_check_params must reject null param before evaluating validation macros',
    ))
    failures.extend(check_function(
        fastfirstpass_text,
        'x265_param_apply_fastfirstpass',
        'if (!param)',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_fastfirstpass requires a non-null parameter struct\\n");',
        'return;',
        'if (param->rc.bStatWrite && !param->rc.bStatRead)',
        'x265_param_apply_fastfirstpass must reject null param before touching rate-control fields',
    ))
    failures.extend(check_function(
        print_params_text,
        'x265_print_params',
        'if (!param)',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_print_params requires a non-null parameter struct\\n");',
        'return;',
        'if (param->logLevel < X265_LOG_INFO)',
        'x265_print_params must reject null param before reading logLevel',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check public param API null guards')
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

    print('Public param API null guards validated')


if __name__ == '__main__':
    main()
