#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/level.cpp')


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
    func_text = extract_braced_block(text, 'int x265_param_apply_profile(x265_param *param, const char *profile)')
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing x265_param_apply_profile function')]

    failures = []
    snippets = (
        'if (!param)',
        'x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_profile requires a non-null parameter struct\\n");',
        'return -1;',
        'if (!profile)',
        'return 0;',
        '#ifdef SVT_HEVC',
    )
    for snippet in snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing x265_param_apply_profile null guardrail: {snippet}'))

    param_pos = func_text.find('if (!param)')
    log_pos = func_text.find(
        'x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_profile requires a non-null parameter struct\\n");',
        param_pos if param_pos != -1 else 0,
    )
    fail_pos = func_text.find('return -1;', log_pos if log_pos != -1 else 0)
    profile_pos = func_text.find('if (!profile)', fail_pos if fail_pos != -1 else 0)
    success_pos = func_text.find('return 0;', profile_pos if profile_pos != -1 else 0)
    svt_pos = func_text.find('#ifdef SVT_HEVC', success_pos if success_pos != -1 else 0)
    if -1 in (param_pos, log_pos, fail_pos, profile_pos, success_pos, svt_pos) or not (
        param_pos < log_pos < fail_pos < profile_pos < success_pos < svt_pos
    ):
        failures.append((
            TARGET.as_posix(),
            0,
            'x265_param_apply_profile must reject null param before handling optional profile no-op or SVT/profile logic',
        ))

    bad_merged_guard = 'if (!param || !profile)'
    if bad_merged_guard in func_text:
        failures.append((
            TARGET.as_posix(),
            0,
            'x265_param_apply_profile must not treat null param and null profile as the same success path',
        ))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_param_apply_profile null guard')
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

    print('x265_param_apply_profile null guard validated')


if __name__ == '__main__':
    main()
