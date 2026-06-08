#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_function(func_text, label, guard_snippet, required_snippet):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    for snippet in (guard_snippet, 'return -1;', required_snippet):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} output null guardrail: {snippet}'))

    guard_pos = func_text.find(guard_snippet)
    return_pos = func_text.find('return -1;', guard_pos if guard_pos != -1 else 0)
    req_pos = func_text.find(required_snippet, return_pos if return_pos != -1 else 0)
    if -1 in (guard_pos, return_pos, req_pos) or not (guard_pos < return_pos < req_pos):
        failures.append((TARGET.as_posix(), 0, f'{label} must reject null output pointers before delegating to encoder state'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    slicetype_text = extract_braced_block(text, 'int x265_get_slicetype_poc_and_scenecut(x265_encoder *enc, int *slicetype, int *poc, int *sceneCut)')
    ref_text = extract_braced_block(text, 'int x265_get_ref_frame_list(x265_encoder *enc, x265_picyuv** l0, x265_picyuv** l1, int sliceType, int poc, int* pocL0, int* pocL1)')

    failures = []
    failures.extend(check_function(
        slicetype_text,
        'x265_get_slicetype_poc_and_scenecut',
        'if (!enc || !slicetype || !poc || !sceneCut)',
        'if (!encoder->copySlicetypePocAndSceneCut(slicetype, poc, sceneCut, 0))',
    ))
    failures.extend(check_function(
        ref_text,
        'x265_get_ref_frame_list',
        'if (!enc || !l0 || !l1 || !pocL0 || !pocL1)',
        'return encoder->getRefFrameList((PicYuv**)l0, (PicYuv**)l1, sliceType, poc, pocL0, pocL1);',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check query API output null guards')
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

    print('Query API output null guards validated')


if __name__ == '__main__':
    main()
