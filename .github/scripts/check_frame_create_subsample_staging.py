#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/frame.cpp')
SIGNATURE = 'bool Frame::createSubSample()'


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
    failures = []
    if '#include <new>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing frame createSubSample staging guardrail: #include <new>'))

    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        failures.append((TARGET.as_posix(), 0, 'missing Frame::createSubSample function'))
        return failures

    required = (
        'PicYuv* stagedFencPicSubsampled2 = new (std::nothrow) PicYuv;',
        'PicYuv* stagedFencPicSubsampled4 = new (std::nothrow) PicYuv;',
        'int* stagedIsSubSampled = nullptr;',
        'if (!stagedFencPicSubsampled2 || !stagedFencPicSubsampled4)',
        'if (!stagedFencPicSubsampled2->createScaledPicYUV(m_param, 2))',
        'if (!stagedFencPicSubsampled4->createScaledPicYUV(m_param, 4))',
        'CHECKED_MALLOC_ZERO(stagedIsSubSampled, int, 1);',
        'm_fencPicSubsampled2 = stagedFencPicSubsampled2;',
        'm_fencPicSubsampled4 = stagedFencPicSubsampled4;',
        'm_isSubSampled = stagedIsSubSampled;',
        'stagedFencPicSubsampled2->destroy();',
        'delete stagedFencPicSubsampled2;',
        'stagedFencPicSubsampled4->destroy();',
        'delete stagedFencPicSubsampled4;',
        'X265_FREE(stagedIsSubSampled);',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing frame createSubSample staging guardrail: {snippet}'))

    forbidden = (
        'm_fencPicSubsampled2 = new PicYuv;',
        'm_fencPicSubsampled4 = new PicYuv;',
        'CHECKED_MALLOC_ZERO(m_isSubSampled, int, 1);',
    )
    for snippet in forbidden:
        if snippet in func_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden frame createSubSample staging regression: {snippet}'))

    alloc2_pos = func_text.find('PicYuv* stagedFencPicSubsampled2 = new (std::nothrow) PicYuv;')
    alloc4_pos = func_text.find('PicYuv* stagedFencPicSubsampled4 = new (std::nothrow) PicYuv;', alloc2_pos if alloc2_pos != -1 else 0)
    alloc_flag_pos = func_text.find('CHECKED_MALLOC_ZERO(stagedIsSubSampled, int, 1);', alloc4_pos if alloc4_pos != -1 else 0)
    assign2_pos = func_text.find('m_fencPicSubsampled2 = stagedFencPicSubsampled2;', alloc_flag_pos if alloc_flag_pos != -1 else 0)
    assign4_pos = func_text.find('m_fencPicSubsampled4 = stagedFencPicSubsampled4;', assign2_pos if assign2_pos != -1 else 0)
    assign_flag_pos = func_text.find('m_isSubSampled = stagedIsSubSampled;', assign4_pos if assign4_pos != -1 else 0)
    if -1 in (alloc2_pos, alloc4_pos, alloc_flag_pos, assign2_pos, assign4_pos, assign_flag_pos) or not (alloc2_pos < alloc4_pos < alloc_flag_pos < assign2_pos < assign4_pos < assign_flag_pos):
        failures.append((TARGET.as_posix(), 0, 'Frame::createSubSample must fully stage subsampled picture state before assigning member state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Frame::createSubSample staging guard')
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

    print('Frame::createSubSample staging guard validated')


if __name__ == '__main__':
    main()
