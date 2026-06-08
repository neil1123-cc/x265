#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/frame.cpp')
SIGNATURE = 'bool Frame::create(x265_param *param, float* quantOffsets)'


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing Frame::create function')]

    failures = []
    required = (
        'if (!m_mcstffencPic->create(param, m_param->bCopyPicToFrame != 0))',
        'return false;',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing frame create MCSTF fenc pic guardrail: {snippet}'))

    forbidden = 'm_mcstffencPic->create(param, m_param->bCopyPicToFrame != 0);'
    if forbidden in func_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden frame create MCSTF fenc pic regression: ignored PicYuv::create() result'))

    temporal_filter_pos = func_text.find('if (m_param->bEnableTemporalFilter)')
    guard_pos = func_text.find('if (!m_mcstffencPic->create(param, m_param->bCopyPicToFrame != 0))', temporal_filter_pos if temporal_filter_pos != -1 else 0)
    if -1 in (temporal_filter_pos, guard_pos) or not (temporal_filter_pos < guard_pos):
        failures.append((TARGET.as_posix(), 0, 'Frame::create must check MCSTF PicYuv::create() inside the temporal filter setup block'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Frame::create MCSTF fenc PicYuv guards')
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

    print('Frame::create MCSTF fenc PicYuv guards validated')


if __name__ == '__main__':
    main()
