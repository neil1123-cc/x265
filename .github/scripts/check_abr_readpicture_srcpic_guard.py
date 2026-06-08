#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);',
    'if (!srcPic)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing input picture at queue position %d for view %d\\n", readPos, view);',
    'm_ret = 4;',
    'return false;',
    'copyInputPictureState(pic, srcPic);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR readPicture srcPic guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
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

    read_picture_text = extract_braced_block('bool PassEncoder::readPicture(x265_picture* dstPic, int view)')

    src_pos = read_picture_text.find('x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);')
    guard_pos = read_picture_text.find('if (!srcPic)', src_pos if src_pos != -1 else 0)
    return_pos = read_picture_text.find('return false;', guard_pos if guard_pos != -1 else 0)
    copy_pos = read_picture_text.find('copyInputPictureState(pic, srcPic);', return_pos if return_pos != -1 else 0)
    if -1 in (src_pos, guard_pos, return_pos, copy_pos) or not (src_pos < guard_pos < return_pos < copy_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::readPicture must guard srcPic before dereferencing it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::readPicture srcPic guard')
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

    print('ABR readPicture srcPic guard validated')


if __name__ == '__main__':
    main()
