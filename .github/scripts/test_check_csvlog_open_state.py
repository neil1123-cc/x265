#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_csvlog_open_state.py')


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
                'source/encoder/api.cpp': '\n'.join((
                    'csvfp = x265_fopen(param->csvfn, "ab");',
                    'if (csvfp && ferror(csvfp))',
                    '{',
                    '    bool closeFailed = ferror(csvfp) != 0;',
                    '    if (fclose(csvfp))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log((x265_param*)param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after append reopen failure\\n", param->csvfn);',
                    '    return nullptr;',
                    '}',
                    'csvfp = x265_fopen(param->csvfn, "wb");',
                    'if (ferror(csvfp))',
                    '{',
                    '    bool closeFailed = ferror(csvfp) != 0;',
                    '    if (fclose(csvfp))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log((x265_param*)param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after create failure\\n", param->csvfn);',
                    '    return nullptr;',
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
                'source/encoder/api.cpp': 'csvfp = x265_fopen(param->csvfn, "ab");\nreturn csvfp;\n',
            },
        )
        expect_fail(run_checker(root), 'missing CSV log open-state guardrail: if (csvfp && ferror(csvfp))')

    print('CSV log open-state guard tests passed')


if __name__ == '__main__':
    main()
