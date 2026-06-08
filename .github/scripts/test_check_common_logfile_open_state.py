#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_common_logfile_open_state.py')


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
                    'FILE* fp = x265_fopen(param->logfn, "ab");',
                    'if (fp)',
                    '{',
                    '    if (std::ferror(fp))',
                    '    {',
                    '        bool closeFailed = std::ferror(fp) != 0;',
                    '        if (std::fclose(fp))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    '    }',
                    '    else',
                    '    {',
                    '        bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                    '        if (std::fclose(fp))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                    '    }',
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
                'source/common/common.cpp': 'FILE* fp = x265_fopen(param->logfn, "ab");\nif (fp)\n    std::fputs(buffer, fp);\n',
            },
        )
        expect_fail(run_checker(root), 'missing common logfile open-state guardrail: if (std::ferror(fp))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.cpp': '\n'.join((
                    'FILE* fp = x265_fopen(param->logfn, "ab");',
                    'if (fp)',
                    '{',
                    '    bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
                    '    if (std::ferror(fp))',
                    '    {',
                    '        bool closeFailed = std::ferror(fp) != 0;',
                    '        if (std::fclose(fp))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
                    '    }',
                    '    if (std::fclose(fp))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'general_log must reject log file open-state errors before writing')

    print('Common logfile open-state guard tests passed')


if __name__ == '__main__':
    main()
