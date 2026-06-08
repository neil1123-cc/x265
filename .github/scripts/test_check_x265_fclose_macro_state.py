#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_fclose_macro_state.py')


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
                    '/* Close a file */',
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { bool closeFailed = ferror(file) != 0; if (fclose(file)) closeFailed = true; if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
                    '#define x265_fread(val, size, readSize, fileOffset,errorMessage)\\',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/common.h': '#define  x265_fclose(file) if (file != nullptr) fclose(file); file=nullptr;\n'})
        expect_fail(run_checker(root), 'missing x265_fclose macro guardrail: bool closeFailed = ferror(file) != 0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.h': '\n'.join((
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { bool closeFailed = ferror(file) != 0; if (fclose(file)) closeFailed = true; if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { if (ferror(file) || fclose(file)) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden x265_fclose macro close short-circuit regression: #define  x265_fclose(file) do { if ((file) != nullptr) { if (ferror(file) || fclose(file)) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.h': '\n'.join((
                    '/* Close a file */',
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { bool closeFailed = ferror(file) != 0; file = nullptr; if (fclose(file)) closeFailed = true; if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } } while (0)',
                    '#define x265_fread(val, size, readSize, fileOffset,errorMessage)\\',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_fclose macro must finalize the file state before clearing the pointer')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.h': '\n'.join((
                    '/* Close a file */',
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { bool closeFailed = ferror(file) != 0; if (fclose(file)) closeFailed = true; if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
                    '#define  x265_fclose(file) do { if ((file) != nullptr) { bool closeFailed = ferror(file) != 0; if (fclose(file)) closeFailed = true; if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
                    '#define x265_fread(val, size, readSize, fileOffset,errorMessage)\\',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_fclose macro guard must define exactly one close macro in the common.h close-file section')

    print('x265_fclose macro guard tests passed')


if __name__ == '__main__':
    main()
