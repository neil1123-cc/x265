#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/threadpool.cpp')
REQUIRED_SNIPPETS = (
    '#include <cctype>',
    'char* end = nullptr;',
    'while (end && *end && std::isspace(static_cast<unsigned char>(*end)))',
    "return errno != ERANGE && end != value && end && *end == '\\0' && std::isfinite(mhz);",
    'if (parseThreadPoolCpuMhzValue(value, mhz) && mhz > maxMhz)',
)
FORBIDDEN_SNIPPETS = (
    'if (errno != ERANGE && end != value && std::isfinite(mhz) && mhz > maxMhz)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing threadpool CPU frequency tail guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden threadpool CPU frequency tail regression: {snippet}'))

    skip_pos = text.find('while (end && *end && std::isspace(static_cast<unsigned char>(*end)))')
    check_pos = text.find("return errno != ERANGE && end != value && end && *end == '\\0' && std::isfinite(mhz);")
    if -1 not in (skip_pos, check_pos) and not (skip_pos < check_pos):
        failures.append((TARGET.as_posix(), 0, 'threadpool CPU frequency parser must trim trailing whitespace before accepting the parsed value'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check threadpool CPU frequency trailing-token guardrail')
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

    print('Threadpool CPU frequency tail guard validated')


if __name__ == '__main__':
    main()
