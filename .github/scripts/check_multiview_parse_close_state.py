#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(this->multiViewConfig) || std::fclose(this->multiViewConfig)',
)
REQUIRED_SNIPPETS = (
    'if (!this->parseMultiViewConfig(inputfn))',
    'bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
    'if (std::fclose(this->multiViewConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after parse failure\\n");',
    'this->multiViewConfig = nullptr;',
    'return true;',
    'return false;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden multiview parse short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing multiview parse close-state guardrail: {snippet}'))

    block = 'if (!this->parseMultiViewConfig(inputfn))'
    block_pos = text.find(block)
    return_pos = text.find('return true;', block_pos if block_pos >= 0 else 0)
    if block_pos < 0 or return_pos < block_pos:
        failures.append((TARGET.as_posix(), 0, 'multiview parse failure must stop CLI parsing after cleanup'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check multiview parse close state')
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

    print('Multiview parse close-state guard validated')


if __name__ == '__main__':
    main()
