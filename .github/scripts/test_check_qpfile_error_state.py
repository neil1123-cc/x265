#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_qpfile_error_state.py')


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
                'source/x265cli.cpp': '\n'.join((
                    'if (!std::fgets(line, sizeof(line), qpfile))',
                    '{',
                    '    if (std::ferror(qpfile))',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "Unable to read qpfile while parsing frame %d\\n", pic_org.poc);',
                    '        return false;',
                    '    }',
                    '    break;',
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
                'source/x265cli.cpp': '\n'.join((
                    'if (!std::fgets(line, sizeof(line), qpfile))',
                    '    break;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing qpfile error-state guardrail: if (std::ferror(qpfile))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'if (!std::fgets(line, sizeof(line), qpfile))',
                    '{',
                    '    break;',
                    '    if (std::ferror(qpfile))',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "Unable to read qpfile while parsing frame %d\\n", pic_org.poc);',
                    '        return false;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'qpfile parsing must distinguish read errors from clean EOF before breaking')

    print('QPFile error-state guard tests passed')


if __name__ == '__main__':
    main()
