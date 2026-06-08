#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lambda_file_error_state.py')


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
                'source/common/param.cpp': '\n'.join((
                    'if (!fgets(line, sizeof(line), lfn))',
                    '{',
                    '    if (ferror(lfn))',
                    '    {',
                    '        bool closeFailed = ferror(lfn) != 0;',
                    '        if (fclose(lfn))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                    '        x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    '        return true;',
                    '    }',
                    '    if (t < 2)',
                    '        return true;',
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
                'source/common/param.cpp': '\n'.join((
                    'if (!fgets(line, sizeof(line), lfn))',
                    '{',
                    '    if (t < 2)',
                    '        return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lambda-file error-state guardrail: if (ferror(lfn))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'if (!fgets(line, sizeof(line), lfn))',
                    '{',
                    '    if (t < 2)',
                    '        return true;',
                    '    if (ferror(lfn))',
                    '    {',
                    '        bool closeFailed = ferror(lfn) != 0;',
                    '        if (fclose(lfn))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
                    '        x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
                    '        return true;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'lambda-file parsing must handle fgets() read errors before incomplete/truncated EOF handling')

    print('Lambda-file error-state guard tests passed')


if __name__ == '__main__':
    main()
