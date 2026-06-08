#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'inFrame[layer] = new (std::nothrow) Frame;',
        'if (!inFrame[layer])',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate input frame for layer %d, aborting encode\\n", layer);',
        'Frame* dupFrame = new (std::nothrow) Frame;',
        'if (!dupFrame)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate temporal-filter frame %d, aborting encode\\n", i);',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder encode frame alloc guardrail: {snippet}'))

    forbidden = (
        'inFrame[layer] = new Frame;',
        'Frame* dupFrame = new Frame;',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder encode frame alloc regression: {snippet}'))

    in_frame_alloc_pos = text.find('inFrame[layer] = new (std::nothrow) Frame;')
    in_frame_guard_pos = text.find('if (!inFrame[layer])', in_frame_alloc_pos if in_frame_alloc_pos != -1 else 0)
    in_frame_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate input frame for layer %d, aborting encode\\n", layer);', in_frame_guard_pos if in_frame_guard_pos != -1 else 0)
    dup_alloc_pos = text.find('Frame* dupFrame = new (std::nothrow) Frame;', in_frame_log_pos if in_frame_log_pos != -1 else 0)
    dup_guard_pos = text.find('if (!dupFrame)', dup_alloc_pos if dup_alloc_pos != -1 else 0)
    dup_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate temporal-filter frame %d, aborting encode\\n", i);', dup_guard_pos if dup_guard_pos != -1 else 0)
    if -1 in (in_frame_alloc_pos, in_frame_guard_pos, in_frame_log_pos, dup_alloc_pos, dup_guard_pos, dup_log_pos) or not (
        in_frame_alloc_pos < in_frame_guard_pos < in_frame_log_pos < dup_alloc_pos < dup_guard_pos < dup_log_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Encoder::encode must reject input and temporal-filter Frame allocation failures before use'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Encoder::encode frame allocation guards')
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

    print('Encoder::encode frame allocation guards validated')


if __name__ == '__main__':
    main()
