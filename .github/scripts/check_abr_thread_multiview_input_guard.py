#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_param->numViews > 1)',
    'bool hasPrimaryView = pic_in[0] != nullptr;',
    'if (hasPrimaryView != (pic_in[view] != nullptr))',
    'x265_log(m_param, X265_LOG_ERROR, "Mismatched multiview input state for view %d in %s\\n",',
    'goto fail;',
    'if (inputPicNum == 2)',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR multiview input guardrail: {snippet}'))

    guard_pos = text.find('if (m_param->numViews > 1)')
    primary_pos = text.find('bool hasPrimaryView = pic_in[0] != nullptr;', guard_pos)
    parity_loop_pos = text.find('for (int view = 1; view < viewCount; view++)', primary_pos)
    mismatch_pos = text.find('if (hasPrimaryView != (pic_in[view] != nullptr))', primary_pos)
    encode_pos = text.find('if (inputPicNum == 2)', mismatch_pos)
    if -1 in (guard_pos, primary_pos, parity_loop_pos, mismatch_pos, encode_pos) or not (guard_pos < primary_pos < parity_loop_pos < mismatch_pos < encode_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must validate multiview input parity before encode submission'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread multiview input guard')
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

    print('ABR multiview input guard validated')


if __name__ == '__main__':
    main()
