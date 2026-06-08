#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/y4m.cpp')
SIGNATURE = 'bool Y4MOutput::writePicture(const x265_picture& pic)'
SEEK_SNIPPET = 'failed |= fseeko(ofs, (int64_t)outPicPos, SEEK_SET) != 0;'
FAIL_CHECK = 'if (failed)\n        return false;'
FRAME_SNIPPET = 'failed |= std::fwrite("FRAME\\n", 1, 6, ofs) != 6;'


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
    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing Y4MOutput::writePicture function')]

    failures = []
    for snippet in (SEEK_SNIPPET, FAIL_CHECK, FRAME_SNIPPET):
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing Y4M recon seek guardrail: {snippet}'))

    seek_pos = func_text.find(SEEK_SNIPPET)
    fail_pos = func_text.find(FAIL_CHECK, seek_pos if seek_pos != -1 else 0)
    frame_pos = func_text.find(FRAME_SNIPPET, fail_pos if fail_pos != -1 else 0)
    if -1 in (seek_pos, fail_pos, frame_pos) or not (seek_pos < fail_pos < frame_pos):
        failures.append((TARGET.as_posix(), 0, 'Y4MOutput::writePicture must return on seek failure before writing the FRAME header'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Y4M recon seek guard')
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

    print('Y4M recon seek guard validated')


if __name__ == '__main__':
    main()
