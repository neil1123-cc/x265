#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_param->numViews > 1 && m_param->bField && m_param->interlaceMode)',
    'x265_log(m_param, X265_LOG_ERROR, "Multiview field/interlace encoding is not supported in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
)
FORBIDDEN_SNIPPETS = (
    'picInput = *pic_in ? (inputNum ? &picField2 : &picField1) : nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR multiview-field guardrail: {snippet}'))

    guard_pos = text.find('if (m_param->numViews > 1 && m_param->bField && m_param->interlaceMode)')
    field_submit_pos = text.find('picInput = *pic_in ? (inputNum ? &picField2 : &picField1) : nullptr;')
    if field_submit_pos != -1 and (guard_pos == -1 or guard_pos > field_submit_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must reject multiview field mode before shared field pictures reach encode submission'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread multiview field guard')
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

    print('ABR multiview field guard validated')


if __name__ == '__main__':
    main()
