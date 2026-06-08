#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
    'if (err) {',
    'printf("problem flushing context\\n");',
    'goto free_data;',
    'free_data:',
    'delete[] ref_data;',
    'delete[] main_data;',
    'delete[] temp_data;',
    'end:',
    'vmaf_model_destroy(model);',
    'vmaf_model_collection_destroy(model_collection);',
    'vmaf_close(vmaf);',
    'return err;',
)
FORBIDDEN_SNIPPETS = (
    'printf("problem flushing context\\n");\n\t\treturn err;',
)
REGION_START = 'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);'
REGION_END = 'return err;'


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
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    if -1 not in (region_start, region_end):
        region_end += len(REGION_END)
        region = text[region_start:region_end]
    else:
        region = text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF flush cleanup regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF flush cleanup guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                'if (err) {',
                'printf("problem flushing context\\n");',
                'goto free_data;',
                'free_data:',
                'delete[] ref_data;',
                'delete[] main_data;',
                'delete[] temp_data;',
                'end:',
                'vmaf_model_destroy(model);',
                'vmaf_model_collection_destroy(model_collection);',
                'vmaf_close(vmaf);',
                'return err;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'VMAF flush failure must flow through free_data before the final model and context teardown'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF flush cleanup guardrails')
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

    print('VMAF flush cleanup validated')


if __name__ == '__main__':
    main()
