#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_fps_parse_safety.py')


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
    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
    'uint32_t parsedNumerator = 0;',
    'uint32_t parsedDenominator = 0;',
    "if (parseOptionUintPair(value, '/', parsedNumerator, parsedDenominator) && parsedNumerator > 0 && parsedDenominator > 0)",
    'numerator = parsedNumerator;',
    'denominator = parsedDenominator;',
    'if (!value || !parseOptionDoubleToken(value, std::strlen(value), fps) || fps <= 0 || fps > INT_MAX)',
    'if (bLocalError || integerFps <= 0)',
    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
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
                'source/common/param.cpp': 'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)\n',
            },
        )
        expect_fail(run_checker(root), 'missing fps parse guardrail: function definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                    '{',
                    "    if (parseOptionUintPair(value, '/', numerator, denominator))",
                    '        return true;',
                    '}',
                    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden fps parse regression: missing positive numerator/denominator guard')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                    '{',
                    "    if (parseOptionUintPair(value, '/', numerator, denominator) && numerator > 0 && denominator > 0)",
                    '        return true;',
                    '}',
                    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden fps parse regression: direct fps pair writes')

    print('FPS parse safety tests passed')


if __name__ == '__main__':
    main()
