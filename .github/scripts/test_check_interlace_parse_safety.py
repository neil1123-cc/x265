#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_interlace_parse_safety.py')


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
    'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'parsedValue = boolValue;',
    'int namedValue = parseName(value, names, bLocalError);',
    'parsedValue = namedValue;',
    'OPT("interlace")',
    '{',
    '    bool bInterlaceBoolError = false;',
    '    int interlaceBoolValue = x265_atobool(value, bInterlaceBoolError);',
    '    bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode)',
    '           || (!bInterlaceBoolError && interlaceBoolValue)',
    '           || p->interlaceMode < 0 || p->interlaceMode > 2;',
    '}',
    'CHECK(param->interlaceMode < 0 || param->interlaceMode > 2,',
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
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing interlace parse guardrail: helper definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'parsedValue = boolValue;',
                    'parsedValue = x265_atobool(value, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden interlace parse regression: helper must not write parsedValue before bool parse succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'parsedValue = namedValue;',
                    'parsedValue = parseName(value, names, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden interlace parse regression: helper must not write parsedValue before named parse succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)',
                    'int boolValue = x265_atobool(value, bLocalError);',
                    'parsedValue = boolValue;',
                    'int namedValue = parseName(value, names, bLocalError);',
                    'parsedValue = namedValue;',
                    'OPT("interlace")',
                    '    {',
                    '        bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode);',
                    '    }',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden interlace parse regression: missing immediate range guard')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '           || (!bInterlaceBoolError && interlaceBoolValue)\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden interlace parse regression: missing bool-true rejection')

    print('Interlace parse safety tests passed')


if __name__ == '__main__':
    main()
