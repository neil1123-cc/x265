#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_help_exit_cleanup.py')


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
                    'parseExitCode = -1;',
                    'parseExitCode = 1;',
                    "case 'h':",
                    '    printVersion(param, api);',
                    '    parseExitCode = 0;',
                    '    showHelp(param);',
                    '    return false;',
                    'OPT("fullhelp")',
                    '{',
                    '    param->logLevel = X265_LOG_FULL;',
                    '    printVersion(param, api);',
                    '    parseExitCode = 0;',
                    '    showHelp(param);',
                    '    return false;',
                    '}',
                    "case 'V':",
                    '    x265_report_simd(param);',
                    '    parseExitCode = 0;',
                    '    return false;',
                    'showHelp(param);',
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
                    "case 'h':",
                    '    showHelp(param);',
                    '    return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing CLI help-exit cleanup guardrail: parseExitCode = -1;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': "case 'V':\n    x265_report_simd(param);\n    std::exit(0);\n",
            },
        )
        expect_fail(run_checker(root), 'forbidden CLI help-exit cleanup regression: std::exit(0);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    "case 'h':",
                    '    printVersion(param, api);',
                    '    parseExitCode = 1;',
                    '    showHelp(param);',
                    '    return false;',
                    'OPT("fullhelp")',
                    '{',
                    '    param->logLevel = X265_LOG_FULL;',
                    '    printVersion(param, api);',
                    '    parseExitCode = 1;',
                    '    showHelp(param);',
                    '    return false;',
                    '}',
                    'parseExitCode = -1;',
                    'parseExitCode = 1;',
                    "case 'V':",
                    '    x265_report_simd(param);',
                    '    parseExitCode = 0;',
                    '    return false;',
                    'showHelp(param);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI help path must exit successfully after printing help')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'parseExitCode = -1;',
                    'parseExitCode = 1;',
                    "case 'h':",
                    '    printVersion(param, api);',
                    '    parseExitCode = 0;',
                    '    showHelp(param);',
                    '    return false;',
                    'OPT("fullhelp")',
                    '{',
                    '    param->logLevel = X265_LOG_FULL;',
                    '    printVersion(param, api);',
                    '    parseExitCode = 0;',
                    '    showHelp(param);',
                    '    return false;',
                    '}',
                    "case 'V':",
                    '    x265_report_simd(param);',
                    '    return false;',
                    '    parseExitCode = 0;',
                    'showHelp(param);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI version path must set parseExitCode and return false without terminating the process')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'parseExitCode = -1;',
                    'parseExitCode = 1;',
                    "case 'h':",
                    '    printVersion(param, api);',
                    '    parseExitCode = 0;',
                    '    showHelp(param);',
                    '    return false;',
                    "case 'V':",
                    '    x265_report_simd(param);',
                    '    parseExitCode = 0;',
                    '    return false;',
                    'OPT("fullhelp")',
                    '{',
                    '    param->logLevel = X265_LOG_FULL;',
                    '    printVersion(param, api);',
                    '    showHelp(param);',
                    '    return false;',
                    '    parseExitCode = 0;',
                    '}',
                    'showHelp(param);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI fullhelp path must exit successfully after printing help')

    print('CLI help/version cleanup guard tests passed')


if __name__ == '__main__':
    main()
