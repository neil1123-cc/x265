#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/matroska_ebml.cpp')


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
    close_text = extract_braced_block(text, 'int mk_close( mk_writer *w, int64_t last_delta )')
    if not close_text:
        return [(TARGET.as_posix(), 0, 'missing mk_close function')]

    required = (
        'if( std::fseek( w->fp, w->duration_ptr, SEEK_SET ) == 0 )',
        'mk_write_float_raw( w->root, (float)((double)total_duration / w->timescale) )',
        'mk_flush_context_data( w->root ) < 0',
        'else',
        'bool closeFailed = std::ferror( w->fp ) != 0;',
        'if( std::fclose( w->fp ) )',
        'if( closeFailed )',
        'ret = -1;',
        'return ret;',
    )
    for snippet in required:
        if snippet not in close_text:
            failures.append((TARGET.as_posix(), 0, f'missing MKV writer close-state guardrail: {snippet}'))

    if 'std::fseek( w->fp, w->duration_ptr, SEEK_SET );' in close_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden MKV writer close-state regression: std::fseek( w->fp, w->duration_ptr, SEEK_SET );'))

    seek_pos = close_text.find('if( std::fseek( w->fp, w->duration_ptr, SEEK_SET ) == 0 )')
    write_pos = close_text.find('mk_write_float_raw( w->root, (float)((double)total_duration / w->timescale) )', seek_pos if seek_pos != -1 else 0)
    flush_pos = close_text.find('mk_flush_context_data( w->root ) < 0', write_pos if write_pos != -1 else 0)
    else_pos = close_text.find('else', flush_pos if flush_pos != -1 else 0)
    else_fail_pos = close_text.find('ret = -1;', else_pos if else_pos != -1 else 0)
    fclose_pos = close_text.find('bool closeFailed = std::ferror( w->fp ) != 0;', else_fail_pos if else_fail_pos != -1 else 0)
    fclose_fail_pos = close_text.find('ret = -1;', fclose_pos if fclose_pos != -1 else 0)
    return_pos = close_text.find('return ret;', fclose_fail_pos if fclose_fail_pos != -1 else 0)
    if -1 in (seek_pos, write_pos, flush_pos, else_pos, else_fail_pos, fclose_pos, fclose_fail_pos, return_pos) or not (
        seek_pos < write_pos < flush_pos < else_pos < else_fail_pos < fclose_pos < fclose_fail_pos < return_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'mk_close must skip duration backfill writes when seeking to the MKV duration field fails'))
    if 'std::ferror( w->fp ) || std::fclose( w->fp )' in close_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden MKV writer close-state short-circuit close regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MKV writer close state')
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

    print('MKV writer close-state guard validated')


if __name__ == '__main__':
    main()
