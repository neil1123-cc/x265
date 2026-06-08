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


def check_function(func_text, label, required_snippet):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} parser'))
        return failures

    name_snippet = 'if (!name)\n        return X265_PARAM_BAD_NAME;'
    p_snippet = 'if (!p)\n        return X265_PARAM_BAD_VALUE;'
    for snippet in (name_snippet, p_snippet, required_snippet):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} null guardrail: {snippet}'))

    name_pos = func_text.find(name_snippet)
    p_pos = func_text.find(p_snippet, name_pos if name_pos != -1 else 0)
    req_pos = func_text.find(required_snippet, p_pos if p_pos != -1 else 0)
    if -1 in (name_pos, p_pos, req_pos) or not (name_pos < p_pos < req_pos):
        failures.append((TARGET.as_posix(), 0, f'{label} must reject null p after validating name and before dereferencing parser state'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    scenecut_text = extract_braced_block(text, 'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)')
    zone_text = extract_braced_block(text, 'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)')

    failures = []
    failures.extend(check_function(scenecut_text, 'x265_scenecut_aware_qp_param_parse', 'p->bEnableSceneCutAwareQp = sceneCutAwareQp;'))
    failures.extend(check_function(zone_text, 'x265_zone_param_parse', 'p->maxNumReferences = maxNumReferences;'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265 zone/scenecut param parse null guards')
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

    print('x265 zone/scenecut param parse null guards validated')


if __name__ == '__main__':
    main()
