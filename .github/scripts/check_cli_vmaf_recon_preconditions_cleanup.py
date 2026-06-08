#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
RECON_REQUIRED_BRANCH = 'x265_log(param, X265_LOG_ERROR, "recon file must be specified to get VMAF score, try --help for help\\n");'
RECON_WRITABLE_BRANCH = 'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");'
INPUT_LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
RECON_LOOP = 'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)'
REQUIRED_SNIPPETS = (
    RECON_REQUIRED_BRANCH,
    RECON_WRITABLE_BRANCH,
    INPUT_LOOP,
    RECON_LOOP,
    'if (this->input[releaseIdx])',
    'this->input[releaseIdx]->release();',
    'this->input[releaseIdx] = nullptr;',
    'if (this->recon[releaseIdx])',
    'this->recon[releaseIdx]->release();',
    'this->recon[releaseIdx] = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI VMAF recon precondition cleanup guardrail: {snippet}'))

    required_pos = text.find(RECON_REQUIRED_BRANCH)
    required_input_loop_pos = text.find(INPUT_LOOP, required_pos)
    required_input_release_pos = text.find('this->input[releaseIdx]->release();', required_input_loop_pos)
    required_return_pos = text.find('return true;', required_input_release_pos)
    if -1 in (required_pos, required_input_loop_pos, required_input_release_pos, required_return_pos) or not (required_pos < required_input_loop_pos < required_input_release_pos < required_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI VMAF recon-required failure must release started inputs before returning'))

    writable_pos = text.find(RECON_WRITABLE_BRANCH)
    writable_input_loop_pos = text.find(INPUT_LOOP, writable_pos)
    writable_input_release_pos = text.find('this->input[releaseIdx]->release();', writable_input_loop_pos)
    writable_recon_loop_pos = text.find(RECON_LOOP, writable_input_release_pos)
    writable_recon_release_pos = text.find('this->recon[releaseIdx]->release();', writable_recon_loop_pos)
    writable_return_pos = text.find('return true;', writable_recon_release_pos)
    if -1 in (writable_pos, writable_input_loop_pos, writable_input_release_pos, writable_recon_loop_pos, writable_recon_release_pos, writable_return_pos) or not (writable_pos < writable_input_loop_pos < writable_input_release_pos < writable_recon_loop_pos < writable_recon_release_pos < writable_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI VMAF recon-writable failure must release started inputs and recon handles before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI VMAF recon precondition cleanup')
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

    print('CLI VMAF recon precondition cleanup validated')


if __name__ == '__main__':
    main()
