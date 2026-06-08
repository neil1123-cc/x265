#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *',
    'requiredFieldFrameSize += pic_in[view]->stride[i] *',
    'if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)',
    'X265_FREE(field1Buf);',
    'X265_FREE(field2Buf);',
    'x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\\n",',
    'assert(framesize == requiredFieldFrameSize);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread field-layout guardrail: {snippet}'))

    alloc_pos = text.find('char* field2Buf = X265_MALLOC(char, fieldFrameSize);')
    size_pos = text.find('uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *', alloc_pos)
    guard_pos = text.find('if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)', size_pos)
    plane_pos = text.find('picField1.planes[0] = field1Buf;', guard_pos)
    assert_pos = text.find('assert(framesize == requiredFieldFrameSize);', plane_pos)
    if -1 in (alloc_pos, size_pos, guard_pos, plane_pos, assert_pos) or not (alloc_pos < size_pos < guard_pos < plane_pos < assert_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must validate field layout before assigning field plane pointers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-layout guard')
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

    print('ABR thread field-layout guard validated')


if __name__ == '__main__':
    main()
