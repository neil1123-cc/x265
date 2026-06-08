#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/matroska_ebml.cpp')
REQUIRED_SNIPPETS = (
    'else',
    'w->fp = std::fopen( filename, "wb" );',
    'if( !w->fp )',
    'if( w->fp != stdout && std::ferror( w->fp ) )',
    'bool closeFailed = std::ferror( w->fp ) != 0;',
    'if( std::fclose( w->fp ) )',
    'if( closeFailed )',
    'std::fprintf( stderr, "x265 [warning]: unable to close MKV writer file after open failure\\n" );',
    'mk_destroy_contexts( w );',
    'std::free( w );',
    'return nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing MKV writer open-state guardrail: {snippet}'))

    fopen_pos = text.find('w->fp = std::fopen( filename, "wb" );')
    null_pos = text.find('if( !w->fp )', fopen_pos)
    ferror_pos = text.find('if( w->fp != stdout && std::ferror( w->fp ) )', null_pos)
    close_state_pos = text.find('bool closeFailed = std::ferror( w->fp ) != 0;', ferror_pos if ferror_pos != -1 else 0)
    cleanup_pos = text.find('mk_destroy_contexts( w );', ferror_pos)
    if -1 in (fopen_pos, null_pos, ferror_pos, close_state_pos, cleanup_pos) or not (fopen_pos < null_pos < ferror_pos < close_state_pos < cleanup_pos):
        failures.append((TARGET.as_posix(), 0, 'MKV writer must clean up open-state failures before returning'))
    if 'std::ferror( w->fp ) || std::fclose( w->fp )' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden MKV writer open-state short-circuit close regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MKV writer open state')
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

    print('MKV writer open-state guard validated')


if __name__ == '__main__':
    main()
