#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mkv.cpp')
REQUIRED_SNIPPETS = (
    'if (!p_mkv || !p_mkv->w)',
    'b_fail = true;',
    'mk_writer* writer = p_mkv->w;',
    'p_mkv->w = nullptr;',
    'p_mkv->b_writing_frame = 0;',
    'if (mk_close(writer, i_last_delta) < 0)',
)


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
    close_text = extract_braced_block(text, 'void MKVOutput::closeFile(int64_t largest_pts, int64_t second_largest_pts)')
    if not close_text:
        return [(TARGET.as_posix(), 0, 'missing MKVOutput::closeFile function')]

    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in close_text:
            failures.append((TARGET.as_posix(), 0, f'missing MKV close fail-state guardrail: {snippet}'))

    if 'if (mk_close(p_mkv->w, i_last_delta) < 0)' in close_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden MKV close fail-state regression: if (mk_close(p_mkv->w, i_last_delta) < 0)'))

    if 'if (b_fail || !p_mkv || !p_mkv->w)' in close_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden MKV close fail-state regression: if (b_fail || !p_mkv || !p_mkv->w)'))

    guard_pos = close_text.find('if (!p_mkv || !p_mkv->w)')
    writer_pos = close_text.find('mk_writer* writer = p_mkv->w;', guard_pos if guard_pos != -1 else 0)
    null_pos = close_text.find('p_mkv->w = nullptr;', writer_pos if writer_pos != -1 else 0)
    frame_pos = close_text.find('p_mkv->b_writing_frame = 0;', null_pos if null_pos != -1 else 0)
    close_pos = close_text.find('if (mk_close(writer, i_last_delta) < 0)', frame_pos if frame_pos != -1 else 0)
    if -1 in (guard_pos, writer_pos, null_pos, frame_pos, close_pos) or not (guard_pos < writer_pos < null_pos < frame_pos < close_pos):
        failures.append((TARGET.as_posix(), 0, 'MKV close must detach the freed writer and clear frame state before calling mk_close, even after prior write failures'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MKV close fail state')
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

    print('MKV close fail-state guard validated')


if __name__ == '__main__':
    main()
