#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);',
    'if (err) {',
    'printf("problem reading pictures\\n");',
    'goto free_data;',
)
FORBIDDEN_SNIPPETS = (
    'printf("problem reading pictures\\n");\n\t\t\tbreak;',
    'printf("problem reading pictures\\n");\n            break;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF picture-read failure regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF picture-read failure guardrail: {snippet}'))

    read_pos = text.find('err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);')
    err_pos = text.find('if (err) {', read_pos if read_pos != -1 else 0)
    log_pos = text.find('printf("problem reading pictures\\n");', err_pos if err_pos != -1 else 0)
    goto_pos = text.find('goto free_data;', log_pos if log_pos != -1 else 0)
    flush_pos = text.find('err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);', goto_pos if goto_pos != -1 else 0)
    if -1 in (read_pos, err_pos, log_pos, goto_pos, flush_pos) or not (read_pos < err_pos < log_pos < goto_pos < flush_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF compute path must abort before flush/scoring when vmaf_read_pictures fails'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF picture-read failure handling')
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

    print('VMAF picture-read failure handling validated')


if __name__ == '__main__':
    main()
