#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
FORBIDDEN_SNIPPETS = (
    'if (feof(user_data->reference_file))',
    'if (feof(user_data->distorted_file))',
    'ret = 2; // OK if end of file',
)
REQUIRED_SNIPPETS = (
    'size_t rowBytes = fread(tmp_buf, 1, width, file);',
    'if (!rowBytes && std::feof(file) && !i)',
    'size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word',
    'if (!rowWords && std::feof(file) && !i)',
    'if (ret == 2)',
    'x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");',
    'x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");',
    'x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF frame read regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF frame read guardrail: {snippet}'))

    byte_read_pos = text.find('size_t rowBytes = fread(tmp_buf, 1, width, file);')
    byte_eof_pos = text.find('if (!rowBytes && std::feof(file) && !i)', byte_read_pos if byte_read_pos != -1 else 0)
    byte_ret_pos = text.find('ret = 2;', byte_eof_pos if byte_eof_pos != -1 else 0)
    word_read_pos = text.find('size_t rowWords = fread(tmp_buf, 2, width, file); // \'2\' for word')
    word_eof_pos = text.find('if (!rowWords && std::feof(file) && !i)', word_read_pos if word_read_pos != -1 else 0)
    word_ret_pos = text.find('ret = 2;', word_eof_pos if word_eof_pos != -1 else 0)
    distorted_eof_pos = text.find('if (ret == 2)')
    distorted_log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "distorted VMAF input ended before reference input\\n");', distorted_eof_pos if distorted_eof_pos != -1 else 0)
    distorted_return_pos = text.find('return 1;', distorted_log_pos if distorted_log_pos != -1 else 0)
    ref_section_start = text.find('// reference skip u and v')
    dist_section_start = text.find('// distorted skip u and v', ref_section_start if ref_section_start != -1 else 0)
    ref_section = text[ref_section_start:dist_section_start] if -1 not in (ref_section_start, dist_section_start) else ''
    dist_section = text[dist_section_start:] if dist_section_start != -1 else ''
    ref_skip_log_pos = ref_section.find('x265_log(nullptr, X265_LOG_ERROR, "reference fread to skip u and v failed.\\n");')
    ref_skip_return_pos = ref_section.find('return 1;', ref_skip_log_pos if ref_skip_log_pos != -1 else 0)
    dist_skip_log_pos = dist_section.find('x265_log(nullptr, X265_LOG_ERROR, "distorted fread to skip u and v failed.\\n");')
    dist_skip_return_pos = dist_section.find('return 1;', dist_skip_log_pos if dist_skip_log_pos != -1 else 0)
    if -1 in (byte_read_pos, byte_eof_pos, byte_ret_pos) or not (byte_read_pos < byte_eof_pos < byte_ret_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF 8-bit frame reads must only treat a zero-byte first-row EOF as a clean end-of-stream'))
    if -1 in (word_read_pos, word_eof_pos, word_ret_pos) or not (word_read_pos < word_eof_pos < word_ret_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF 10-bit frame reads must only treat a zero-word first-row EOF as a clean end-of-stream'))
    if -1 in (distorted_eof_pos, distorted_log_pos, distorted_return_pos) or not (distorted_eof_pos < distorted_log_pos < distorted_return_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF read_frame must reject distorted-input EOF after a reference frame has already been read'))
    if -1 in (ref_section_start, dist_section_start, ref_skip_log_pos, ref_skip_return_pos) or not (ref_skip_log_pos < ref_skip_return_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF read_frame must fail fast when skipping reference chroma data fails'))
    if -1 in (dist_section_start, dist_skip_log_pos, dist_skip_return_pos) or not (dist_skip_log_pos < dist_skip_return_pos):
        failures.append((TARGET.as_posix(), 0, 'VMAF read_frame must fail fast when skipping distorted chroma data fails'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF frame read state handling')
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

    print('VMAF frame read state validated')


if __name__ == '__main__':
    main()
