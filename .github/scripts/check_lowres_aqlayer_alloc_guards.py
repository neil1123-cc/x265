#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/lowres.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'pAQLayer = new (std::nothrow) PicQPAdaptationLayer[4]();',
        'if (!pAQLayer)',
        'if (!pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight))',
        'if (pAQLayer)',
        'delete[] pAQLayer;',
        'pAQLayer = nullptr;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lowres AQ-layer guardrail: {snippet}'))

    forbidden = (
        'pAQLayer = new PicQPAdaptationLayer[4];',
        'pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight);',
        'if (maxAQDepth > 0)',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden lowres AQ-layer regression: {snippet}'))

    alloc_pos = text.find('pAQLayer = new (std::nothrow) PicQPAdaptationLayer[4]();')
    alloc_guard_pos = text.find('if (!pAQLayer)', alloc_pos if alloc_pos != -1 else 0)
    create_guard_pos = text.find('if (!pAQLayer[d].create(origPic->m_picWidth, origPic->m_picHeight, partWidth, partHeight, nAQPartInWidth, nAQPartInHeight))', alloc_guard_pos if alloc_guard_pos != -1 else 0)
    destroy_guard_pos = text.find('if (pAQLayer)', create_guard_pos if create_guard_pos != -1 else 0)
    delete_pos = text.find('delete[] pAQLayer;', destroy_guard_pos if destroy_guard_pos != -1 else 0)
    null_pos = text.find('pAQLayer = nullptr;', delete_pos if delete_pos != -1 else 0)
    if -1 in (alloc_pos, alloc_guard_pos, create_guard_pos, destroy_guard_pos, delete_pos, null_pos) or not (
        alloc_pos < alloc_guard_pos < create_guard_pos < destroy_guard_pos < delete_pos < null_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Lowres HEVC AQ layer allocation and cleanup must guard partial creation before use and during destroy'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Lowres HEVC AQ-layer allocation guards')
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

    print('Lowres AQ-layer allocation guards validated')


if __name__ == '__main__':
    main()
