#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mkv_writer_close_state.py')

# Coverage probes used by the scan for MKV writer close-state guardrails.
NORMALIZED_PROBES = (
    'mk_close must skip duration backfill writes when seeking to the MKV duration field fails',
    'forbidden MKV writer close-state short-circuit close regression',
    'missing MKV writer close-state guardrail: ',
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
                    'int mk_close( mk_writer *w, int64_t last_delta )',
                    '{',
                    '    if( std::fseek( w->fp, w->duration_ptr, SEEK_SET ) == 0 )',
                    '    {',
                    '        if( mk_write_float_raw( w->root, (float)((double)total_duration / w->timescale) ) < 0 ||',
                    '            mk_flush_context_data( w->root ) < 0 )',
                    '            ret = -1;',
                    '    }',
                    '    else',
                    '        ret = -1;',
                    'bool closeFailed = std::ferror( w->fp ) != 0;',
                    'if( std::fclose( w->fp ) )',
                    '    closeFailed = true;',
                    'if( closeFailed )',
                    '    ret = -1;',
                    'return ret;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/matroska_ebml.cpp': 'int mk_close( mk_writer *w, int64_t last_delta )\n{\nstd::fclose( w->fp );\n}\n'})
        expect_fail(run_checker(root), 'missing MKV writer close-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/matroska_ebml.cpp': '\n'.join((
                    'int mk_close( mk_writer *w, int64_t last_delta )',
                    '{',
                    '    std::fseek( w->fp, w->duration_ptr, SEEK_SET );',
                    '    if( mk_write_float_raw( w->root, (float)((double)total_duration / w->timescale) ) < 0 ||',
                    '        mk_flush_context_data( w->root ) < 0 )',
                    '        ret = -1;',
                    '    bool closeFailed = std::ferror( w->fp ) != 0;',
                    '    if( std::fclose( w->fp ) )',
                    '        closeFailed = true;',
                    '    if( closeFailed )',
                    '        ret = -1;',
                    '    return ret;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden MKV writer close-state regression: std::fseek( w->fp, w->duration_ptr, SEEK_SET );')

    print('MKV writer close-state guard tests passed')


if __name__ == '__main__':
    main()
