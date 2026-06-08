#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'FILE *progressfp = x265_fopen(param->pgfn, "wb");',
    'bool wroteProgress = std::fprintf(progressfp,',
    '>= 0;',
    'bool closeFailed = std::ferror(progressfp) != 0;',
    'if (std::fclose(progressfp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'wroteProgress = false;',
    'if (wroteProgress)',
    'prevUpdateTimeFile = time;',
    'else',
    'x265_log_file(param, X265_LOG_WARNING, "unable to open progress report file \\"%s\\"\\n", param->pgfn);',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI progress-file guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI progress file state')
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

    print('CLI progress-file guard validated')


if __name__ == '__main__':
    main()
