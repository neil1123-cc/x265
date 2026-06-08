#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
ERROR_SNIPPET = 'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");'
LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
REQUIRED_SNIPPETS = (
    ERROR_SNIPPET,
    LOOP,
    'if (this->input[releaseIdx])',
    'this->input[releaseIdx]->release();',
    'this->input[releaseIdx] = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI recon basename cleanup guardrail: {snippet}'))

    first_error_pos = text.find(ERROR_SNIPPET)
    first_loop_pos = text.find(LOOP, first_error_pos)
    first_release_pos = text.find('this->input[releaseIdx]->release();', first_loop_pos)
    first_return_pos = text.find('return true;', first_release_pos)
    if -1 in (first_error_pos, first_loop_pos, first_release_pos, first_return_pos) or not (first_error_pos < first_loop_pos < first_release_pos < first_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI recon basename failure must release started inputs before returning'))

    second_error_pos = text.find(ERROR_SNIPPET, first_return_pos)
    second_loop_pos = text.find(LOOP, second_error_pos)
    second_release_pos = text.find('this->input[releaseIdx]->release();', second_loop_pos)
    second_return_pos = text.find('return true;', second_release_pos)
    if -1 in (second_error_pos, second_loop_pos, second_release_pos, second_return_pos) or not (second_error_pos < second_loop_pos < second_release_pos < second_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI empty recon basename failure must release started inputs before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI recon basename cleanup')
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

    print('CLI recon basename cleanup validated')


if __name__ == '__main__':
    main()
