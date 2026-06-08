#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.cpp')
REQUIRED_SNIPPETS = (
    'FILE* fp = x265_fopen(param->logfn, "ab");',
    'if (fp)',
    'if (std::ferror(fp))',
    'bool closeFailed = std::ferror(fp) != 0;',
    'if (std::fclose(fp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
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
            failures.append((TARGET.as_posix(), 0, f'missing common logfile open-state guardrail: {snippet}'))

    open_pos = text.find('FILE* fp = x265_fopen(param->logfn, "ab");')
    open_guard_pos = text.find('if (fp)', open_pos)
    ferror_pos = text.find('if (std::ferror(fp))', open_guard_pos)
    write_pos = text.find('bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);', ferror_pos)
    if -1 in (open_pos, open_guard_pos, ferror_pos, write_pos) or not (open_pos < open_guard_pos < ferror_pos < write_pos):
        failures.append((TARGET.as_posix(), 0, 'general_log must reject log file open-state errors before writing'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check common logfile open state')
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

    print('Common logfile open-state guard validated')


if __name__ == '__main__':
    main()
