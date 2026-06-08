#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_options_fail_state.py')

# Coverage probe used by the scan for GOP options fail-state guardrails.
NORMALIZED_PROBES = (
    'missing GOP options fail-state guardrail: ',
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
                    'if (b_fail || !gop_file)',
                    '{',
                    '    b_fail = true;',
                    '    return;',
                    '}',
                    'if (std::fprintf(gop_file, "#options %s.options\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '{',
                    '    b_fail = true;',
                    '    std::fclose(opt_file);',
                    '    return;',
                    '}',
                    'bool closeFailed = std::ferror(opt_file) != 0;',
                    'if (std::fclose(opt_file))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    b_fail = true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/gop.cpp': 'std::fclose(opt_file);\n'})
        expect_fail(run_checker(root), 'missing GOP options fail-state guardrail')

    print('GOP options fail-state guard tests passed')


if __name__ == '__main__':
    main()
