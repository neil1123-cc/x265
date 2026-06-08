#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
BRANCH = 'x265_log_file(param, X265_LOG_ERROR, "failed to open output file <%s> for writing\\n", outputfn);'
INPUT_LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
RECON_LOOP = 'for (int releaseIdx = 0; releaseIdx < param->numLayers; releaseIdx++)'
REQUIRED_SNIPPETS = (
    BRANCH,
    'if (this->output)',
    'this->output->release();',
    'this->output = nullptr;',
    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");',
    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after output open failure");',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI output failure cleanup guardrail: {snippet}'))

    branch_pos = text.find(BRANCH)
    output_release_pos = text.find('this->output->release();', branch_pos)
    reference_close_pos = text.find('closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");', output_release_pos)
    distorted_close_pos = text.find('closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after output open failure");', reference_close_pos)
    input_loop_pos = text.find(INPUT_LOOP, distorted_close_pos)
    input_release_pos = text.find('this->input[releaseIdx]->release();', input_loop_pos)
    recon_loop_pos = text.find(RECON_LOOP, input_release_pos)
    recon_release_pos = text.find('this->recon[releaseIdx]->release();', recon_loop_pos)
    return_pos = text.find('return true;', recon_release_pos)
    if -1 in (branch_pos, output_release_pos, reference_close_pos, distorted_close_pos, input_loop_pos, input_release_pos, recon_loop_pos, recon_release_pos, return_pos) or not (branch_pos < output_release_pos < reference_close_pos < distorted_close_pos < input_loop_pos < input_release_pos < recon_loop_pos < recon_release_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI output-open failure must release output, VMAF files, started inputs, and recon handles before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI output failure full cleanup')
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

    print('CLI output failure cleanup validated')


if __name__ == '__main__':
    main()
