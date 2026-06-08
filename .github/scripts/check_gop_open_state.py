#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
REQUIRED_SNIPPETS = (
    'FILE* fp = x265_fopen(fname.c_str(), "wb");',
    'if(fp != nullptr && !std::ferror(fp))',
    'if (fp != nullptr)',
    'bool closeFailed = std::ferror(fp) != 0;',
    'if (std::fclose(fp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'general_log(nullptr, getName(), X265_LOG_WARNING,',
    '"unable to close file %s after open failure.\\n", fname.c_str());',
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
            failures.append((TARGET.as_posix(), 0, f'missing GOP open-state guardrail: {snippet}'))

    open_pos = text.find('FILE* fp = x265_fopen(fname.c_str(), "wb");')
    return_pos = text.find('if(fp != nullptr && !std::ferror(fp))', open_pos)
    cleanup_pos = text.find('if (fp != nullptr)', return_pos)
    retry_pos = text.find('if(!retry)', cleanup_pos)
    if -1 in (open_pos, return_pos, cleanup_pos, retry_pos) or not (open_pos < return_pos < cleanup_pos < retry_pos):
        failures.append((TARGET.as_posix(), 0, 'GOP file open-state cleanup must happen before retry/bailout'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP open state')
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

    print('GOP open-state guard validated')


if __name__ == '__main__':
    main()
