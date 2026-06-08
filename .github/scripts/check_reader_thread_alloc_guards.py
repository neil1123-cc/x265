#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'x265_picture* src = x265_picture_alloc();',
    'if (!src)',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input picture\\n");',
    'm_parentEnc->m_ret = 4;',
    'm_parentEnc->m_inputOver.store(true);',
    'm_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
    'if (!dest->planes[0])',
    'dest->planes[0] = X265_MALLOC(char, dest->framesize);',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input plane\\n");',
    'std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing reader thread alloc guardrail: {snippet}'))

    alloc_pos = text.find('x265_picture* src = x265_picture_alloc();')
    guard_pos = text.find('if (!src)', alloc_pos)
    init_pos = text.find('x265_picture_init(m_parentEnc->m_param, src);', alloc_pos)
    if -1 not in (alloc_pos, guard_pos, init_pos) and not (alloc_pos < guard_pos < init_pos):
        failures.append((TARGET.as_posix(), 0, 'Reader::threadMain must guard src allocation before x265_picture_init'))

    plane_guard_pos = text.find('if (!dest->planes[0])')
    plane_alloc_pos = text.find('dest->planes[0] = X265_MALLOC(char, dest->framesize);', plane_guard_pos)
    memcpy_pos = text.find('std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));', plane_alloc_pos)
    if -1 not in (plane_guard_pos, plane_alloc_pos, memcpy_pos) and not (plane_guard_pos < plane_alloc_pos < memcpy_pos):
        failures.append((TARGET.as_posix(), 0, 'Reader::threadMain must guard late plane allocation before memcpy'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Reader::threadMain allocation guards')
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

    print('Reader thread allocation guards validated')


if __name__ == '__main__':
    main()
