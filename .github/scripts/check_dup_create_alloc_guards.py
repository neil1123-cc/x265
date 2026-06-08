#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'm_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));',
    'if (!m_dupBuffer[i])',
    'm_dupBuffer[i]->dupPic = x265_picture_alloc();',
    'if (!m_dupBuffer[i]->dupPic)',
    'm_dupBuffer[i]->dupPlane = X265_MALLOC(char, framesize);',
    'if (!m_dupBuffer[i]->dupPlane)',
    'if (!m_dupPicOne[0] || !m_dupPicTwo[0])',
    'if (!m_dupPicOne[k] || !m_dupPicTwo[k])',
    'm_aborted = true;',
    'return;',
)
FORBIDDEN_SNIPPETS = (
    'm_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));\n            m_dupBuffer[i]->dupPic = nullptr;',
    'm_dupPicOne[0] = X265_MALLOC(pixel, size);\n            m_dupPicTwo[0] = X265_MALLOC(pixel, size);\n            if (p->internalCsp != X265_CSP_I400)',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden duplication create alloc regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing duplication create alloc guardrail: {snippet}'))

    buffer_alloc_pos = text.find('m_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));')
    buffer_check_pos = text.find('if (!m_dupBuffer[i])')
    pic_alloc_pos = text.find('m_dupBuffer[i]->dupPic = x265_picture_alloc();')
    pic_check_pos = text.find('if (!m_dupBuffer[i]->dupPic)')
    plane_alloc_pos = text.find('m_dupBuffer[i]->dupPlane = X265_MALLOC(char, framesize);')
    plane_check_pos = text.find('if (!m_dupBuffer[i]->dupPlane)')
    if -1 not in (buffer_alloc_pos, buffer_check_pos, pic_alloc_pos, pic_check_pos, plane_alloc_pos, plane_check_pos):
        if not (buffer_alloc_pos < buffer_check_pos < pic_alloc_pos < pic_check_pos < plane_alloc_pos < plane_check_pos):
            failures.append((TARGET.as_posix(), 0, 'duplication create must check each allocation before dereferencing the next object'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check duplication create allocation guardrails')
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

    print('Duplication create allocation guards validated')


if __name__ == '__main__':
    main()
