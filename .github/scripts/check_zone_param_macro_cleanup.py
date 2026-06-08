#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    '#define atoi(str) x265_atoi(str, bError)',
    '#define atof(str) x265_atof(str, bError)',
    '#define atobool(str) (x265_atobool(str, bError))',
    'OPT("fast-intra") p->bEnableFastIntra = atobool(value);',
)
REQUIRED_SNIPPETS = (
    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
    'OPT("fast-intra") p->bEnableFastIntra = x265_atobool(value, bError);',
    'OPT("tskip-fast") p->bEnableTSkipFast = x265_atobool(value, bError);',
)


def extract_zone_macro_region(text):
    marker = 'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)'
    index = text.find(marker)
    if index < 0:
        return '', ''
    start = text.rfind('/* internal versions of string-to-int with additional error checking */', 0, index)
    if start < 0:
        start = 0
    return text[start:index], text[index:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    macro_text, after_text = extract_zone_macro_region(text)
    if not after_text:
        return [(TARGET.as_posix(), 0, 'missing zone param parser')]

    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in after_text and snippet not in macro_text:
            failures.append((TARGET.as_posix(), 0, f'missing zone param cleanup guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in macro_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden zone param macro regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zone param macro cleanup guardrails')
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

    print('zone param macro cleanup validated')


if __name__ == '__main__':
    main()
