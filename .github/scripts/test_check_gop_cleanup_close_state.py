#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_cleanup_close_state.py')

# Coverage probes used by the scan for GOP cleanup close-state guardrails.
NORMALIZED_PROBES = (
    'forbidden GOP cleanup short-circuit close regression',
    'missing GOP cleanup close guardrail: ',
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
                'source/output/gop.cpp': '\n'.join((
                    'if (data_file)',
                    '{',
                    '    bool closeFailed = std::ferror(data_file) != 0;',
                    '    if (std::fclose(data_file))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        b_fail = true;',
                    '}',
                    'if (gop_file)',
                    '{',
                    '    bool closeFailed = std::ferror(gop_file) != 0;',
                    '    if (std::fclose(gop_file))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        b_fail = true;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/gop.cpp': 'if (data_file && std::fclose(data_file))\n    b_fail = true;\n'})
        expect_fail(run_checker(root), 'missing GOP cleanup close guardrail')

    print('GOP cleanup close guard tests passed')


if __name__ == '__main__':
    main()
