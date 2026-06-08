#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    '#define atoi(str) x265_atoi(str, bError)',
    '#define atof(str) x265_atof(str, bError)',
    '#define atobool(str) (x265_atobool(str, bError))',
)
REQUIRED_SNIPPETS = (
    'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
    'int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);',
    'OPT("masking-strength") bError = parseMaskingStrength(p, value);',
)


def extract_before_function(text):
    marker = 'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)'
    index = text.find(marker)
    if index < 0:
        return '', ''
    return text[:index], text[index:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    before_text, after_text = extract_before_function(text)
    if not after_text:
        return [(TARGET.as_posix(), 0, 'missing scenecut-aware QP parser')]

    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in after_text:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut-aware QP cleanup guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in before_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden scenecut-aware QP macro regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scenecut-aware QP macro cleanup guardrails')
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

    print('scenecut-aware QP macro cleanup validated')


if __name__ == '__main__':
    main()
