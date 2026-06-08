#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (isAbrLoad)',
    'if (!analysisData)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing analysis data for frame %d\\n", ipread);',
    'm_ret = 4;',
    'return false;',
    'pic->analysisData = *analysisData;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR readPicture analysis guardrail: {snippet}'))

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

    load_pos = read_picture_text.find('if (isAbrLoad)')
    guard_pos = read_picture_text.find('if (!analysisData)', load_pos if load_pos != -1 else 0)
    return_pos = read_picture_text.find('return false;', guard_pos if guard_pos != -1 else 0)
    assign_pos = read_picture_text.find('pic->analysisData = *analysisData;', return_pos if return_pos != -1 else 0)
    if -1 in (load_pos, guard_pos, return_pos, assign_pos) or not (load_pos < guard_pos < return_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::readPicture must guard analysisData before copying it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::readPicture analysis guard')
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

    print('ABR readPicture analysis guard validated')


if __name__ == '__main__':
    main()
