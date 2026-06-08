#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("log-file")',
    'char* newLogFile = strdup(value);',
    'if (!newLogFile)',
    'free(p->logfn);',
    'p->logfn = newLogFile;',
    'OPT("progress-file")',
    'char* newProgressFile = strdup(value);',
    'if (!newProgressFile)',
    'free(p->pgfn);',
    'p->pgfn = newProgressFile;',
)
FORBIDDEN_SNIPPETS = (
    'if (p->logfn)',
    'p->logfn = nullptr;',
    'p->logfn = strdup(value);',
    'if (p->pgfn)',
    'p->pgfn = nullptr;',
    'p->pgfn = strdup(value);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    log_block_start = text.find('OPT("log-file")')
    progress_block_start = text.find('OPT("progress-file")')
    if log_block_start == -1 or progress_block_start == -1:
        return [(TARGET.as_posix(), 0, 'missing log/progress file option block')]

    log_block_end = text.find('OPT("log-file-level")', log_block_start)
    progress_block_end = text.find('OPT("csv-log-level")', progress_block_start)
    log_block = text[log_block_start:log_block_end if log_block_end != -1 else None]
    progress_block = text[progress_block_start:progress_block_end if progress_block_end != -1 else None]

    scoped_checks = (
        (log_block, FORBIDDEN_SNIPPETS[:3], REQUIRED_SNIPPETS[:5]),
        (progress_block, FORBIDDEN_SNIPPETS[3:], REQUIRED_SNIPPETS[5:]),
    )
    for block_text, forbidden_snippets, required_snippets in scoped_checks:
        for snippet in forbidden_snippets:
            if snippet in block_text:
                failures.append((TARGET.as_posix(), 0, f'forbidden log/progress file parse regression: {snippet}'))
        for snippet in required_snippets:
            if snippet not in block_text:
                failures.append((TARGET.as_posix(), 0, f'missing log/progress file guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check log/progress file parse safety guardrails')
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

    print('Log/progress file parse safety validated')


if __name__ == '__main__':
    main()
