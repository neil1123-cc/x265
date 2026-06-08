#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_inputfn_alloc_guard.py')


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
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    'for (int view = 0; view < MAX_VIEWS; view++)',
                    '{',
                    'inputfn[view] = X265_MALLOC(char, sizeof(char) * 1024);',
                    'if (!inputfn[view])',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate input filename buffer\\n");',
                    '    return true;',
                    '}',
                    'std::fill_n(inputfn[view], 1024, char(0));',
                    '}',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    '    return false;',
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
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    'for (int view = 0; view < MAX_VIEWS; view++)',
                    '{',
                    'inputfn[view] = X265_MALLOC(char, sizeof(char) * 1024);',
                    'std::fill_n(inputfn[view], 1024, char(0));',
                    '}',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing cli inputfn alloc guardrail: if (!inputfn[view])')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    'for (int view = 0; view < MAX_VIEWS; view++)',
                    '{',
                    'std::fill_n(inputfn[view], 1024, char(0));',
                    'inputfn[view] = X265_MALLOC(char, sizeof(char) * 1024);',
                    'if (!inputfn[view])',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate input filename buffer\\n");',
                    '    return true;',
                    '}',
                    '}',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI input filename buffer must be checked before zero-fill')

    print('CLI input filename allocation guard tests passed')


if __name__ == '__main__':
    main()
