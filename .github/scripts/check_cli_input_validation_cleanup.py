#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
DEPTH_BRANCH = 'if (info[i].depth < 8 || info[i].depth > 16)'
DEPTH_LOOP = 'for (int releaseIdx = 0; releaseIdx <= i; releaseIdx++)'
MULTIVIEW_BRANCH = 'x265_log(param, X265_LOG_ERROR, "Multiview input file <%s> does not match the first view\\n", inputfn[i]);'
MULTIVIEW_LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
REQUIRED_SNIPPETS = (
    DEPTH_BRANCH,
    DEPTH_LOOP,
    MULTIVIEW_BRANCH,
    MULTIVIEW_LOOP,
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI input validation cleanup guardrail: {snippet}'))

    depth_pos = text.find(DEPTH_BRANCH)
    depth_loop_pos = text.find(DEPTH_LOOP, depth_pos)
    depth_release_pos = text.find('this->input[releaseIdx]->release();', depth_loop_pos)
    depth_return_pos = text.find('return true;', depth_release_pos)
    if -1 in (depth_pos, depth_loop_pos, depth_release_pos, depth_return_pos) or not (depth_pos < depth_loop_pos < depth_release_pos < depth_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI input bit-depth validation must release opened inputs before returning'))

    multiview_pos = text.find(MULTIVIEW_BRANCH)
    multiview_loop_pos = text.find(MULTIVIEW_LOOP, multiview_pos)
    multiview_release_pos = text.find('this->input[releaseIdx]->release();', multiview_loop_pos)
    multiview_return_pos = text.find('return true;', multiview_release_pos)
    if -1 in (multiview_pos, multiview_loop_pos, multiview_release_pos, multiview_return_pos) or not (multiview_pos < multiview_loop_pos < multiview_release_pos < multiview_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI multiview validation must release opened inputs before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI input validation cleanup')
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

    print('CLI input validation cleanup validated')


if __name__ == '__main__':
    main()
