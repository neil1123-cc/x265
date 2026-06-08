#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mp4.cpp')
SIGNATURE = 'bool MP4Muxer::configureParameterSets(const x265_nal* nal, uint32_t nalcount)'


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


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if '#include <new>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing MP4 header SEI allocation guardrail: #include <new>'))

    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        failures.append((TARGET.as_posix(), 0, 'missing MP4Muxer::configureParameterSets function'))
        return failures

    required = (
        'newSeiBuffer = new (std::nothrow) uint8_t[newSeiSize];',
        'if (!newSeiBuffer)',
        'return failSeiAssembly("failed to allocate sei transition buffer.\\n");',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing MP4 header SEI allocation guardrail: {snippet}'))

    forbidden = (
        'newSeiBuffer = new uint8_t[newSeiSize];',
    )
    for snippet in forbidden:
        if snippet in func_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden MP4 header SEI allocation regression: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MP4 header SEI allocation guard')
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

    print('MP4 header SEI allocation guard validated')


if __name__ == '__main__':
    main()
