#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_common_logfile_close_state.py')


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
                'source/common/common.cpp': '\n'.join((
                    'if (std::ferror(fp))',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    'else',
                    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/common.cpp': 'std::fputs(buffer, fp);\nstd::fclose(fp);\n'})
        expect_fail(run_checker(root), 'missing common logfile close guardrail: if (std::ferror(fp))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'if (std::ferror(fp))',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    'else',
                    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                    'if (std::ferror(fp) || std::fclose(fp))',
                    '    std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden common logfile short-circuit close regression: std::ferror(fp) || std::fclose(fp)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'if (std::ferror(fp))',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    'else',
                    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                    'std::fclose(fp);',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected guarded log-file fclose handling in both the open-failure and finalize branches')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'if (std::ferror(fp))',
                    '    bool closeFailed = std::ferror(fp) != 0;',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    'else',
                    'if (std::fclose(fp))',
                    '    closeFailed = true;',
                    'std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'common logfile close guards must preserve the open-failure branch before the finalize branch')

    print('Common logfile close guard tests passed')


if __name__ == '__main__':
    main()
