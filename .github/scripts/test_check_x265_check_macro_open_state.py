#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_check_macro_open_state.py')


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
                'source/common/common.h': '\n'.join((
                    '#define X265_CHECK(expr, ...) if (!(expr)) { \\',
                    '    x265_log(nullptr, X265_LOG_ERROR, __VA_ARGS__); \\',
                    '    FILE *fp = fopen("x265_check_failures.txt", "a"); \\',
                    '    if (fp) { if (ferror(fp)) { bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n"); } else { fprintf(fp, "%s:%d\\n", __FILE__, __LINE__); fprintf(fp, __VA_ARGS__); bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n"); } } \\',
                    '    g_checkFailures++; DEBUG_BREAK(); \\',
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
                'source/common/common.h': '#define X265_CHECK(expr, ...) if (!(expr)) { FILE *fp = fopen("x265_check_failures.txt", "a"); if (fp) { fprintf(fp, __VA_ARGS__); } }\n',
            },
        )
        expect_fail(run_checker(root), 'missing x265 check macro open-state guardrail: if (fp) { if (ferror(fp)) { bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n"); } else { fprintf(fp, "%s:%d\\n", __FILE__, __LINE__); fprintf(fp, __VA_ARGS__); bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n"); } }')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.h': '\n'.join((
                    '#define X265_CHECK(expr, ...) if (!(expr)) { \\',
                    '    x265_log(nullptr, X265_LOG_ERROR, __VA_ARGS__); \\',
                    '    FILE *fp = fopen("x265_check_failures.txt", "a"); \\',
                    '    if (fp) { else { fprintf(fp, "%s:%d\\n", __FILE__, __LINE__); fprintf(fp, __VA_ARGS__); } if (ferror(fp)) { bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n"); } } \\',
                    '    g_checkFailures++; DEBUG_BREAK(); \\',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'X265_CHECK must reject open-state errors before writing the failure log')

    print('x265 check macro open-state guard tests passed')


if __name__ == '__main__':
    main()
