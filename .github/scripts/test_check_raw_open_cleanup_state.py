#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_raw_open_cleanup_state.py')

# Coverage probes used by the scan for raw open cleanup-state guardrails.
NORMALIZED_PROBES = (
    'missing raw open cleanup-state guardrail: ',
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
                'source/output/raw.cpp': '\n'.join((
                    'ofs = x265_fopen(fname, "wb");',
                    'if (!ofs)',
                    '    b_fail = true;',
                    'else if (std::ferror(ofs))',
                    '    bool closeFailed = std::ferror(ofs) != 0;',
                    '    if (std::fclose(ofs))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log(nullptr, X265_LOG_WARNING, "raw: unable to close output file after open failure\\n");',
                    '    ofs = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/raw.cpp': '\n'.join((
                    'ofs = x265_fopen(fname, "wb");',
                    'if (!ofs || std::ferror(ofs))',
                    '    b_fail = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing raw open cleanup-state guardrail')

    print('RAW open cleanup-state guard tests passed')


if __name__ == '__main__':
    main()
