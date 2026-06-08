#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mkv_header_cleanup_state.py')

# Coverage probe used by the scan for MKV header cleanup-state guardrails.
NORMALIZED_PROBES = (
    'missing MKV header cleanup-state guardrail: ',
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
                    'ret = mk_write_header(p_mkv->w, writingApp, "V_MPEGH/ISO/HEVC",',
                    'if (ret < 0)',
                    '{',
                    '    if (mk_close(p_mkv->w, 0) < 0)',
                    '        ERR("Unable to clean up MKV writer after header failure\\n");',
                    '    p_mkv->w = nullptr;',
                    '    b_fail = true;',
                    '    return ret;',
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
                'source/output/mkv.cpp': '\n'.join((
                    'ret = mk_write_header(p_mkv->w, writingApp, "V_MPEGH/ISO/HEVC",',
                    'if (ret < 0)',
                    '{',
                    '    b_fail = true;',
                    '    return ret;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing MKV header cleanup-state guardrail')

    print('MKV header cleanup-state guard tests passed')


if __name__ == '__main__':
    main()
