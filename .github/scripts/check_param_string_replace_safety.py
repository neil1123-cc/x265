#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'char* newLogfn = nullptr;',
    'newLogfn = strdup(src->logfn);',
    'if (newLogfn)',
    'free(dst->logfn);',
    'dst->logfn = newLogfn;',
    'char* newPgfn = nullptr;',
    'newPgfn = strdup(src->pgfn);',
    'if (newPgfn)',
    'free(dst->pgfn);',
    'dst->pgfn = newPgfn;',
)
FORBIDDEN_SNIPPETS = (
    'if (dst->logfn)\n    {\n        free(dst->logfn);\n        dst->logfn = nullptr;\n    }\n    if (src->logfn)',
    'if (dst->pgfn)\n    {\n        free(dst->pgfn);\n        dst->pgfn = nullptr;\n    }\n    if (src->pgfn)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden param string replacement regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing param string replacement guardrail: {snippet}'))

    log_strdup = text.find('newLogfn = strdup(src->logfn);')
    log_free = text.find('free(dst->logfn);')
    log_assign = text.find('dst->logfn = newLogfn;')
    if -1 not in (log_strdup, log_free, log_assign) and not (log_strdup < log_free < log_assign):
        failures.append((TARGET.as_posix(), 0, 'logfn replacement must allocate before dropping the old string'))

    pg_strdup = text.find('newPgfn = strdup(src->pgfn);')
    pg_free = text.find('free(dst->pgfn);')
    pg_assign = text.find('dst->pgfn = newPgfn;')
    if -1 not in (pg_strdup, pg_free, pg_assign) and not (pg_strdup < pg_free < pg_assign):
        failures.append((TARGET.as_posix(), 0, 'pgfn replacement must allocate before dropping the old string'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check param string replacement safety guardrails')
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

    print('Param string replacement safety validated')


if __name__ == '__main__':
    main()
