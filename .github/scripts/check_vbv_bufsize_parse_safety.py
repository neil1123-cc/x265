#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("vbv-bufsize")',
    'bool bVbvBufsizeError = false;',
    'int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);',
    'bError |= bVbvBufsizeError;',
    'if (!bVbvBufsizeError)',
    'svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;',
)
FORBIDDEN_SNIPPET = 'OPT("vbv-bufsize") svtHevcParam->vbvBufsize = (uint32_t)x265_atoi(value, bError);'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')

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

    svt_param_text = extract_braced_block('int svt_param_parse(x265_param* param, const char* name, const char* value)')
    failures = []
    if FORBIDDEN_SNIPPET in svt_param_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT vbv-bufsize regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in svt_param_text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT vbv-bufsize guardrail: {snippet}'))

    def extract_option_block(option_name, required_inner_snippet=None):
        search_from = 0
        needle = f'OPT("{option_name}")'
        while True:
            start = svt_param_text.find(needle, search_from)
            if start == -1:
                return svt_param_text
            next_opt = svt_param_text.find('OPT("', start + len(needle))
            brace_start = svt_param_text.find('{', start + len(needle))
            if brace_start != -1 and (next_opt == -1 or brace_start < next_opt):
                depth = 0
                for idx in range(brace_start, len(svt_param_text)):
                    char = svt_param_text[idx]
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            block = svt_param_text[start:idx + 1]
                            if required_inner_snippet is None or required_inner_snippet in block:
                                return block
                            break
                else:
                    block = svt_param_text[start:]
                    if required_inner_snippet is None or required_inner_snippet in block:
                        return block
            search_from = start + len(needle)

    parse_block = extract_option_block('vbv-bufsize', 'svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;')
    parse_pos = parse_block.find('int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);')
    error_pos = parse_block.find('bError |= bVbvBufsizeError;', parse_pos if parse_pos != -1 else 0)
    guard_pos = parse_block.find('if (!bVbvBufsizeError)', error_pos if error_pos != -1 else 0)
    assign_pos = parse_block.find('svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;', guard_pos if guard_pos != -1 else 0)
    if -1 in (parse_pos, error_pos, guard_pos, assign_pos) or not (parse_pos < error_pos < guard_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'SVT vbv-bufsize parse block must gate assignment on parseOptionIntValue success'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check vbv-bufsize parse safety guardrails')
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

    print('SVT vbv-bufsize parse safety validated')


if __name__ == '__main__':
    main()
