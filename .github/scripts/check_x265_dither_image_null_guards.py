#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
SIGNATURE = 'void x265_dither_image(x265_picture* picIn, int picWidth, int picHeight, int16_t *errorBuf, int bitDepth)'
BRANCH = 'if (!picIn || !errorBuf)'
LOG = 'fprintf(stderr, "extras [error]: x265_dither_image requires non-null picture and error buffer\\n");'
RETURN = 'return;'
API = 'const x265_api* api = x265_api_get(0);'
SKEW = 'if (!api || sizeof(x265_picture) != api->sizeof_picture)'


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
        return [(TARGET.as_posix(), 0, 'missing x265_dither_image function')]

    failures = []
    for snippet in (BRANCH, LOG, RETURN, API, SKEW):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing x265_dither_image null guardrail: {snippet}'))

    branch_pos = func_text.find(BRANCH)
    log_pos = func_text.find(LOG, branch_pos if branch_pos != -1 else 0)
    return_pos = func_text.find(RETURN, log_pos if log_pos != -1 else 0)
    api_pos = func_text.find(API, return_pos if return_pos != -1 else 0)
    skew_pos = func_text.find(SKEW, api_pos if api_pos != -1 else 0)
    if -1 in (branch_pos, log_pos, return_pos, api_pos, skew_pos) or not (branch_pos < log_pos < return_pos < api_pos < skew_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_dither_image must reject null picture/error buffer before querying API sizes or dereferencing picture state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_dither_image null guards')
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

    print('x265_dither_image null guards validated')


if __name__ == '__main__':
    main()
