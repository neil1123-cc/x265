#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
REQUIRED_SNIPPETS = (
    '#include <cerrno>',
    'errno = 0;',
    "if (*cursor == '-')",
    'if (errno == ERANGE || end == cursor || parsedFirst > UINT_MAX || *end != separator)',
    'if (errno == ERANGE || end == cursor || parsedSecond > UINT_MAX || (*end != \' \' && *end != \'\\0\'))',
    'double parsed = std::strtod(token, &end);',
    "if (errno == ERANGE || !end || *end != '\\0' || end == token || !std::isfinite(parsed))",
)
FORBIDDEN_SNIPPETS = (
    'if (end == cursor || parsed < INT_MIN || parsed > INT_MAX || (*end != \' \' && *end != \'\\0\'))',
    'if (end == cursor || parsedFirst > UINT_MAX || *end != separator)',
    'if (end == cursor || parsedSecond > UINT_MAX || (*end != \' \' && *end != \'\\0\'))',
    'if (end == cursor || !std::isfinite(parsed) || (*end != \' \' && *end != \'\\0\'))',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if text.count('errno = 0;') < 3:
        failures.append((TARGET.as_posix(), 0, 'expected errno reset in all reviewed ratecontrol numeric parse helpers'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol numeric helper regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol numeric helper guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ratecontrol numeric parse helper safety guardrails')
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

    print('Ratecontrol numeric helper safety validated')


if __name__ == '__main__':
    main()
