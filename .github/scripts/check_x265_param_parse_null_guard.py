#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'if (!name)\n        return X265_PARAM_BAD_NAME;',
    'if (!p)\n        return X265_PARAM_BAD_VALUE;',
    'if (p->bEnableSvtHevc)',
    'p->cpuid = X265_NS::cpu_detect(true);',
)


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
    func_text = extract_braced_block(text, 'int x265_param_parse(x265_param* p, const char* name, const char* value)')
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing x265_param_parse parser')]

    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing x265_param_parse null guardrail: {snippet}'))

    name_pos = func_text.find('if (!name)\n        return X265_PARAM_BAD_NAME;')
    p_pos = func_text.find('if (!p)\n        return X265_PARAM_BAD_VALUE;', name_pos if name_pos != -1 else 0)
    svt_pos = func_text.find('if (p->bEnableSvtHevc)', p_pos if p_pos != -1 else 0)
    cpu_pos = func_text.find('p->cpuid = X265_NS::cpu_detect(true);', svt_pos if svt_pos != -1 else 0)
    if -1 in (name_pos, p_pos, svt_pos, cpu_pos) or not (name_pos < p_pos < svt_pos < cpu_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_param_parse must reject null p after validating name and before dereferencing parser state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_param_parse null guard')
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

    print('x265_param_parse null guard validated')


if __name__ == '__main__':
    main()
