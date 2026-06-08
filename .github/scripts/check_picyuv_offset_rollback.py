#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/picyuv.cpp')
ANCHOR = 'bool PicYuv::createOffsets(const SPS& sps)'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    func_pos = text.find(ANCHOR)
    destroy_pos = text.find('void PicYuv::destroy()', func_pos if func_pos != -1 else 0)
    if func_pos == -1:
        return [(TARGET.as_posix(), 0, 'unable to locate PicYuv::createOffsets')]
    if destroy_pos == -1:
        destroy_pos = len(text)

    body = text[func_pos:destroy_pos]

    required = (
        'fail:',
        'X265_FREE(m_buOffsetC);',
        'm_buOffsetC = nullptr;',
        'X265_FREE(m_buOffsetY);',
        'm_buOffsetY = nullptr;',
        'X265_FREE(m_cuOffsetC);',
        'm_cuOffsetC = nullptr;',
        'X265_FREE(m_cuOffsetY);',
        'm_cuOffsetY = nullptr;',
        'return false;',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing PicYuv offset rollback guardrail: {snippet}'))

    fail_pos = body.find('fail:')
    free_bu_c_pos = body.find('X265_FREE(m_buOffsetC);', fail_pos if fail_pos != -1 else 0)
    null_bu_c_pos = body.find('m_buOffsetC = nullptr;', free_bu_c_pos if free_bu_c_pos != -1 else 0)
    free_bu_y_pos = body.find('X265_FREE(m_buOffsetY);', null_bu_c_pos if null_bu_c_pos != -1 else 0)
    null_bu_y_pos = body.find('m_buOffsetY = nullptr;', free_bu_y_pos if free_bu_y_pos != -1 else 0)
    free_cu_c_pos = body.find('X265_FREE(m_cuOffsetC);', null_bu_y_pos if null_bu_y_pos != -1 else 0)
    null_cu_c_pos = body.find('m_cuOffsetC = nullptr;', free_cu_c_pos if free_cu_c_pos != -1 else 0)
    free_cu_y_pos = body.find('X265_FREE(m_cuOffsetY);', null_cu_c_pos if null_cu_c_pos != -1 else 0)
    null_cu_y_pos = body.find('m_cuOffsetY = nullptr;', free_cu_y_pos if free_cu_y_pos != -1 else 0)
    return_pos = body.find('return false;', null_cu_y_pos if null_cu_y_pos != -1 else 0)
    if -1 in (fail_pos, free_bu_c_pos, null_bu_c_pos, free_bu_y_pos, null_bu_y_pos, free_cu_c_pos, null_cu_c_pos, free_cu_y_pos, null_cu_y_pos, return_pos) or not (
        fail_pos < free_bu_c_pos < null_bu_c_pos < free_bu_y_pos < null_bu_y_pos < free_cu_c_pos < null_cu_c_pos < free_cu_y_pos < null_cu_y_pos < return_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'PicYuv::createOffsets must release all partially allocated offset tables before returning failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PicYuv offset rollback guards')
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

    print('PicYuv offset rollback guards validated')


if __name__ == '__main__':
    main()
