#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'char* field1Buf = X265_MALLOC(char, fieldFrameSize);',
    'char* field2Buf = X265_MALLOC(char, fieldFrameSize);',
    'if (!field1Buf || !field2Buf)',
    'X265_FREE(field1Buf);',
    'X265_FREE(field2Buf);',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate field picture buffers for view %d in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread field-buffer guardrail: {snippet}'))

    field1_pos = text.find('char* field1Buf = X265_MALLOC(char, fieldFrameSize);')
    field2_pos = text.find('char* field2Buf = X265_MALLOC(char, fieldFrameSize);', field1_pos)
    guard_pos = text.find('if (!field1Buf || !field2Buf)', field2_pos)
    plane_pos = text.find('picField1.planes[0] = field1Buf;', guard_pos)
    if -1 in (field1_pos, field2_pos, guard_pos, plane_pos) or not (field1_pos < field2_pos < guard_pos < plane_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must guard field picture buffers before assigning plane pointers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-buffer guard')
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

    print('ABR thread field-buffer guard validated')


if __name__ == '__main__':
    main()
