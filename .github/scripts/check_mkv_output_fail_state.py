#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mkv.cpp')
REQUIRED_SNIPPETS = (
    'if (b_fail || !p_mkv || !p_mkv->w)',
    'if (!p_mkv->width || !p_mkv->height ||',
    'b_fail = true;',
    'if (mk_start_frame(p_mkv->w) < 0)',
    'if (mk_add_frame_data(p_mkv->w, p_nal[3].payload, p_nal[3].sizeBytes) < 0)',
    'if (mk_add_frame_data(p_mkv->w, p_nalu[i].payload, p_nalu[i].sizeBytes) < 0)',
    'if (mk_set_frame_flags(p_mkv->w, i_stamp, b_keyframe, b_bframe) < 0)',
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
            failures.append((TARGET.as_posix(), 0, f'missing MKV output fail-state guardrail: {snippet}'))

    if text.count('if (b_fail || !p_mkv || !p_mkv->w)') < 2:
        failures.append((TARGET.as_posix(), 0, 'MKV output must reject writes after fail-state or writer teardown in both header and frame paths'))

    if text.count('b_fail = true;') < 8:
        failures.append((TARGET.as_posix(), 0, 'MKV output must mark fail-state on all write/header error returns'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MKV output fail-state guard')
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

    print('MKV output fail-state guard validated')


if __name__ == '__main__':
    main()
