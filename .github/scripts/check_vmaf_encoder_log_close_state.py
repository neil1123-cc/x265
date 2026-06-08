#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
FORBIDDEN_SNIPPETS = (
    'if (ferror(vmafdata->reference_file) || fclose(vmafdata->reference_file))',
    'if (ferror(vmafdata->distorted_file) || fclose(vmafdata->distorted_file))',
)
REQUIRED_SNIPPETS = (
    'stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);',
    'if(vmafdata->reference_file)',
    'bool closeFailed = ferror(vmafdata->reference_file) != 0;',
    'if (fclose(vmafdata->reference_file))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close VMAF reference file after score calculation\\n");',
    'if(vmafdata->distorted_file)',
    'bool closeFailed = ferror(vmafdata->distorted_file) != 0;',
    'if (fclose(vmafdata->distorted_file))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close VMAF distorted file after score calculation\\n");',
    'x265_free(vmafdata);',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF encoder-log close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF encoder-log close guardrail: {snippet}'))
    score_line = 'stats.aggregateVmafScore = x265_calculate_vmafscore(param, vmafdata);'
    ref_close = 'bool closeFailed = ferror(vmafdata->reference_file) != 0;'
    dist_close = 'bool closeFailed = ferror(vmafdata->distorted_file) != 0;'
    free_line = 'x265_free(vmafdata);'
    score_index = text.find(score_line)
    ref_index = text.find(ref_close)
    dist_index = text.find(dist_close)
    free_index = text.find(free_line)
    if -1 not in (score_index, ref_index, dist_index, free_index):
        if not (score_index < ref_index < dist_index < free_index):
            failures.append((TARGET.as_posix(), 0, 'VMAF close guards must stay after score calculation and before x265_free(vmafdata)'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF encoder log close state')
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

    print('VMAF encoder-log close guard validated')


if __name__ == '__main__':
    main()
