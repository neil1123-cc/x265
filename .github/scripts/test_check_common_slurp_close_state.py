#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_common_slurp_close_state.py')


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
                    'else if (std::ferror(fh))',
                    '    bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
                    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bError |= closeFailed;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
                    'return buf;',
                    'error:',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/common.cpp': 'std::fclose(fh);\n'})
        expect_fail(run_checker(root), 'missing common slurp close guardrail: else if (std::ferror(fh))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'else if (std::ferror(fh))',
                    '    bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
                    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bError |= closeFailed;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
                    'return buf;',
                    'error:',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'bError |= std::ferror(fh) || std::fclose(fh);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden common slurp short-circuit close regression: bError |= std::ferror(fh) || std::fclose(fh);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'else if (std::ferror(fh))',
                    '    bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
                    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bError |= closeFailed;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
                    'return buf;',
                    'error:',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'std::fclose(fh);',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected three guarded common slurp fclose calls')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'else if (std::ferror(fh))',
                    '    bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
                    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bError |= closeFailed;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
                    'return buf;',
                    'error:',
                    'fclose(fh);',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'expected guarded common slurp close handling in the open-failure, read-complete, and error-cleanup paths')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'else if (std::ferror(fh))',
                    '    bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
                    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'bError |= closeFailed;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
                    'error:',
                    'bool closeFailed = std::ferror(fh) != 0;',
                    'if (std::fclose(fh))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
                    'return buf;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'common slurp close guards must preserve the early open-failure, read-complete, and error-cleanup ordering')

    print('Common slurp close guard tests passed')


if __name__ == '__main__':
    main()
