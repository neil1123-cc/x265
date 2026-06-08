#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (pic_in[view]->framesize)',
    'if (!pic_in[view]->planes[i] || !picField1.planes[i] || !picField2.planes[i])',
    'x265_log(m_param, X265_LOG_ERROR, "Missing field plane state for view %d plane %d in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
    'char* srcP1 = (char*)pic_in[view]->planes[i];',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread field-plane guardrail: {snippet}'))

    frame_pos = text.find('if (pic_in[view]->framesize)')
    plane_guard_pos = text.find('if (!pic_in[view]->planes[i] || !picField1.planes[i] || !picField2.planes[i])', frame_pos)
    src_pos = text.find('char* srcP1 = (char*)pic_in[view]->planes[i];', plane_guard_pos)
    if -1 in (frame_pos, plane_guard_pos, src_pos) or not (frame_pos < plane_guard_pos < src_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must guard field plane state before copying field data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-plane guard')
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

    print('ABR thread field-plane guard validated')


if __name__ == '__main__':
    main()
