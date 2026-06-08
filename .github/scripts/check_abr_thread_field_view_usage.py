#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
    'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[view]->stride[0];',
    'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
    'x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
    'assert(framesize == requiredFieldFrameSize);',
    'fieldBuffersCreated = true;',
)
FORBIDDEN_SNIPPETS = (
    'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[0]->stride[0];',
    'for (int i = 1; i < x265_cli_csps[pic_in[0]->colorSpace].planes; i++)',
)
REGION_START = 'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *'
REGION_END = 'fieldBuffersCreated = true;'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end + len(end_marker)]


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
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread field-view guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR field-view regression: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
                'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                'if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)',
                'x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
                'int stride = picField1.stride[0] = picField2.stride[0] = pic_in[view]->stride[0];',
                'for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                'assert(framesize == requiredFieldFrameSize);',
                'fieldBuffersCreated = true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'ABR field threading must preserve the reviewed view-indexed frame-size validation before publishing per-view field strides and planes'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-view usage')
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

    print('ABR thread field-view usage validated')


if __name__ == '__main__':
    main()
