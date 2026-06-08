#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_log_level_parse_safety.py')


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


PASS_SOURCE = '\n'.join((
    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
    'int maxIndexedValue = indexOffset;',
    'for (const char* const* name = names; name && *name; name++, maxIndexedValue++) {}',
    'int indexedValue = parseOptionIntValue(value, bLocalError);',
    'if (!bLocalError && indexedValue >= indexOffset && indexedValue <= maxIndexedValue)',
    'parsedValue = indexedValue;',
    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logLevel);',
    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logfLevel);',
    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'static bool parseBoolOrIntValue(const char* value, int& parsedValue)\n',
            },
        )
        expect_fail(run_checker(root), 'missing log level parse guardrail: function definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                    '{',
                    '    bool bLocalError = false;',
                    '    parsedValue = x265_atoi(value, bLocalError);',
                    '    if (!bLocalError)',
                    '        return true;',
                    '}',
                    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden log level parse regression: unbounded numeric acceptance')

    print('Log level parse safety tests passed')


if __name__ == '__main__':
    main()
