#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
BRANCH = 'if (!param)'
REQUIRED_SNIPPETS = (
    BRANCH,
    'x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");',
    'return -1;',
    '::x265_param_default(param);',
    'X265_NS::x265_param_default(param);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_pos = text.find('int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)')
    next_func_pos = text.find('#undef atoi', func_pos if func_pos != -1 else 0)
    func_text = text[func_pos:next_func_pos if next_func_pos != -1 else len(text)] if func_pos != -1 else ''

    failures = []
    if func_pos == -1:
        failures.append((TARGET.as_posix(), 0, 'missing x265_param_default_preset declaration'))
        return failures

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing x265_param_default_preset null guardrail: {snippet}'))

    branch_pos = func_text.find(BRANCH)
    log_pos = func_text.find('x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\\n");', branch_pos if branch_pos != -1 else 0)
    return_pos = func_text.find('return -1;', log_pos if log_pos != -1 else 0)
    c_api_pos = func_text.find('::x265_param_default(param);', return_pos if return_pos != -1 else 0)
    ns_pos = func_text.find('X265_NS::x265_param_default(param);', return_pos if return_pos != -1 else 0)
    default_call_pos = c_api_pos if c_api_pos != -1 else ns_pos
    if -1 in (branch_pos, log_pos, return_pos, default_call_pos) or not (branch_pos < log_pos < return_pos < default_call_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_param_default_preset must guard null param before default initialization'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_param_default_preset null guard')
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

    print('x265_param_default_preset null guard validated')


if __name__ == '__main__':
    main()
