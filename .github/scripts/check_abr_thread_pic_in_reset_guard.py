#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'while (pic_in[0] && !b_ctrl_c)',
    'pic_in[view] = &pic_orig[view];',
    'if (!m_cliopt.parseQPFile(pic_orig[view]))',
    'x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
    'pic_orig[view].poc, profileName);',
    'else if (readPicture(pic_in[view], view)){',
)
FORBIDDEN_SNIPPETS = (
    'pic_in[view]->poc, profileName);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread pic_in reset guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR thread pic_in reset regression: {snippet}'))

    loop_pos = text.find('while (pic_in[0] && !b_ctrl_c)')
    reset_pos = text.find('pic_in[view] = &pic_orig[view];', loop_pos)
    qp_pos = text.find('if (!m_cliopt.parseQPFile(pic_orig[view]))', reset_pos)
    read_pos = text.find('else if (readPicture(pic_in[view], view)){', qp_pos)
    if -1 in (loop_pos, reset_pos, qp_pos, read_pos) or not (loop_pos < reset_pos < qp_pos < read_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must reset pic_in[view] before qpfile parsing and readPicture reuse'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread pic_in reset guard')
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

    print('ABR thread pic_in reset guard validated')


if __name__ == '__main__':
    main()
