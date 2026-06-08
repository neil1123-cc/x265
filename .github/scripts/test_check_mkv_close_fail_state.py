#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mkv_close_fail_state.py')

# Coverage probes used by the scan for MKV close fail-state guardrails.
NORMALIZED_PROBES = (
    'forbidden MKV close fail-state regression: if (mk_close(p_mkv->w, i_last_delta) < 0)',
    'missing MKV close fail-state guardrail: ',
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
                'source/output/mkv.cpp': '\n'.join((
                    'void MKVOutput::closeFile(int64_t largest_pts, int64_t second_largest_pts)',
                    '{',
                    'if (!p_mkv || !p_mkv->w)',
                    '    b_fail = true;',
                    '    return;',
                    'mk_writer* writer = p_mkv->w;',
                    'p_mkv->w = nullptr;',
                    'p_mkv->b_writing_frame = 0;',
                    'if (mk_close(writer, i_last_delta) < 0)',
                    '    b_fail = true;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mkv.cpp': 'void MKVOutput::closeFile(int64_t largest_pts, int64_t second_largest_pts)\n{\nmk_close(p_mkv->w, i_last_delta);\n}\n'})
        expect_fail(run_checker(root), 'missing MKV close fail-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mkv.cpp': '\n'.join((
                    'void MKVOutput::closeFile(int64_t largest_pts, int64_t second_largest_pts)',
                    '{',
                    'if (!p_mkv || !p_mkv->w)',
                    '    b_fail = true;',
                    '    return;',
                    'mk_writer* writer = p_mkv->w;',
                    'if (mk_close(writer, i_last_delta) < 0)',
                    '    b_fail = true;',
                    'p_mkv->w = nullptr;',
                    'p_mkv->b_writing_frame = 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'MKV close must detach the freed writer and clear frame state before calling mk_close, even after prior write failures')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mkv.cpp': '\n'.join((
                    'void MKVOutput::closeFile(int64_t largest_pts, int64_t second_largest_pts)',
                    '{',
                    'if (b_fail || !p_mkv || !p_mkv->w)',
                    '    b_fail = true;',
                    '    return;',
                    'mk_writer* writer = p_mkv->w;',
                    'p_mkv->w = nullptr;',
                    'p_mkv->b_writing_frame = 0;',
                    'if (mk_close(writer, i_last_delta) < 0)',
                    '    b_fail = true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden MKV close fail-state regression: if (b_fail || !p_mkv || !p_mkv->w)')

    print('MKV close fail-state guard tests passed')


if __name__ == '__main__':
    main()
