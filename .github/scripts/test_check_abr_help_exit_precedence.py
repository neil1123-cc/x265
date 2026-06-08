#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_help_exit_precedence.py')

# Coverage probes used by the scan for ABR help/exit precedence guardrails.
NORMALIZED_PROBES = (
    'x265 main must detect explicit help/version/fullhelp before abr-ladder parsing',
    'x265 main must preserve parseExitCode handling after CLI parse returns',
    'missing abr/help precedence guardrail: ',
    'forbidden abr/help precedence regression: ',
)


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
                'source/x265cli.h': '\n'.join((
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    '{',
                    "    if (c == 'h' || c == 'V')",
                    '        return true;',
                    '    if (long_options_index >= 0 && !std::strcmp(long_options[long_options_index].name, "fullhelp"))',
                    '        return true;',
                    '}',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
                    'int main(int argc, char **argv)',
                    '{',
                    'bool isCliExitRequest = hasCliExitRequest(argc, argv);',
                    'bool isAbrLadder = !isCliExitRequest && checkAbrLadder(argc, argv, &abrConfig);',
                    'else if (cliopt[0].parseExitCode >= 0)',
                    '    ret = cliopt[0].parseExitCode;',
                    'cleanup:',
                    '    return ret;',
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
                'source/x265cli.h': '\n'.join((
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    '{',
                    "    if (c == 'h' || c == 'V')",
                    '        return true;',
                    '    if (long_options_index >= 0 && !std::strcmp(long_options[long_options_index].name, "fullhelp"))',
                    '        return true;',
                    '}',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
                    'int main(int argc, char **argv)',
                    '{',
                    'bool isAbrLadder = checkAbrLadder(argc, argv, &abrConfig);',
                    'cleanup:',
                    '    return 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden abr/help precedence regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'static inline bool hasCliExitRequest(int argc, char** argv)',
                    '{',
                    "    if (c == 'h' || c == 'V')",
                    '        return true;',
                    '    if (long_options_index >= 0 && !std::strcmp(long_options[long_options_index].name, "fullhelp"))',
                    '        return true;',
                    '}',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
                'source/x265.cpp': '\n'.join((
                    'int main(int argc, char **argv)',
                    '{',
                    'bool isCliExitRequest = hasCliExitRequest(argc, argv);',
                    'bool isAbrLadder = checkAbrLadder(argc, argv, &abrConfig);',
                    'else if (cliopt[0].parseExitCode >= 0)',
                    '    ret = cliopt[0].parseExitCode;',
                    'cleanup:',
                    '    return ret;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden abr/help precedence regression')

    print('ABR/help precedence guard tests passed')


if __name__ == '__main__':
    main()
