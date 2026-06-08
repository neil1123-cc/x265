#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mkv_writer_open_state.py')

# Coverage probes used by the scan for MKV writer open-state guardrails.
NORMALIZED_PROBES = (
    'MKV writer must clean up open-state failures before returning',
    'forbidden MKV writer open-state short-circuit close regression',
    'missing MKV writer open-state guardrail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/matroska_ebml.cpp': '\n'.join((
                    'else',
                    '    w->fp = std::fopen( filename, "wb" );',
                    'if( !w->fp )',
                    '{',
                    '    mk_destroy_contexts( w );',
                    '    std::free( w );',
                    '    return nullptr;',
                    '}',
                    'if( w->fp != stdout && std::ferror( w->fp ) )',
                    '{',
                    '    bool closeFailed = std::ferror( w->fp ) != 0;',
                    '    if( std::fclose( w->fp ) )',
                    '        closeFailed = true;',
                    '    if( closeFailed )',
                    '        std::fprintf( stderr, "x265 [warning]: unable to close MKV writer file after open failure\\n" );',
                    '    mk_destroy_contexts( w );',
                    '    std::free( w );',
                    '    return nullptr;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/matroska_ebml.cpp': 'w->fp = std::fopen( filename, "wb" );\nif( !w->fp ) return nullptr;\n',
            },
        )
        expect_fail(run_checker(root), 'missing MKV writer open-state guardrail')

    print('MKV writer open-state guard tests passed')


if __name__ == '__main__':
    main()
