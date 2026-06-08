#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
ALLOC_REQUIRED_SNIPPETS = (
    'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
    'if (!vmafData)',
    'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
    '*vmafData = x265_vmaf_data();',
)
RECON_REQUIRED_SNIPPETS = (
    'if (!this->recon[0])',
    'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
    'return true;',
)
OPEN_REQUIRED_SNIPPETS = (
    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
    'if (!vmafData->reference_file || !vmafData->distorted_file)',
    'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
    'return true;',
)
FORBIDDEN_SNIPPETS = ()
ALLOC_REGION_START = 'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));'
ALLOC_REGION_END = 'if (api->param_default_preset(param, preset, tune) < 0)'
RECON_REGION_START = 'if (!this->recon[0])'
RECON_REGION_END = "const char *str = std::strrchr(info[0].filename, '.');"
OPEN_REGION_START = 'vmafData->reference_file = x265_fopen(inputfn[0], "rb");'
OPEN_REGION_END = 'if (!vmafData->reference_file || !vmafData->distorted_file ||'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    alloc_region = get_region(text, ALLOC_REGION_START, ALLOC_REGION_END)
    recon_region = get_region(text, RECON_REGION_START, RECON_REGION_END)
    open_region = get_region(text, OPEN_REGION_START, OPEN_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF/recon state regression: {snippet}'))
    for snippet in ALLOC_REQUIRED_SNIPPETS:
        if snippet not in alloc_region:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF/recon guardrail: {snippet}'))
    for snippet in RECON_REQUIRED_SNIPPETS:
        if snippet not in recon_region:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF/recon guardrail: {snippet}'))
    for snippet in OPEN_REQUIRED_SNIPPETS:
        if snippet not in open_region:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF/recon guardrail: {snippet}'))
    if all(snippet in alloc_region for snippet in ALLOC_REQUIRED_SNIPPETS):
        if not has_in_order(
            alloc_region,
            (
                'vmafData = (x265_vmaf_data*)x265_malloc(sizeof(x265_vmaf_data));',
                'if (!vmafData)',
                'x265_log(nullptr, X265_LOG_ERROR, "vmaf data alloc failed\\n");',
                'return true;',
                '*vmafData = x265_vmaf_data();',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'VMAF state initialization must guard the allocation result before zero-initializing vmafData'))
    if all(snippet in recon_region for snippet in RECON_REQUIRED_SNIPPETS):
        if not has_in_order(
            recon_region,
            (
                'if (!this->recon[0])',
                'x265_log(param, X265_LOG_ERROR, "recon file must be writable to get VMAF score\\n");',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'VMAF setup must reject non-writable recon output before attempting to open VMAF input files'))
    if all(snippet in open_region for snippet in OPEN_REQUIRED_SNIPPETS):
        if not has_in_order(
            open_region,
            (
                'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
                'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
                'if (!vmafData->reference_file || !vmafData->distorted_file)',
                'x265_log(param, X265_LOG_ERROR, "unable to open VMAF input files\\n");',
                'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'VMAF input setup must close both staged input files after an open failure before returning'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF and recon state safety guardrails')
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

    print('VMAF/recon state safety validated')


if __name__ == '__main__':
    main()
