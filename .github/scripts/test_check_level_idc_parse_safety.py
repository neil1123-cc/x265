#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_level_idc_parse_safety.py')


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
    'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
    'double scaledLevel = 10 * decimalLevel;',
    'int roundedLevel = (int)(scaledLevel + .5);',
    'if (std::fabs(scaledLevel - roundedLevel) > 1e-6)',
    'parsedLevel = roundedLevel;',
    'if (!parseTenthsOrIntegerLevel(value, p->levelIdc))',
    'if (!parseTenthsOrIntegerLevel(value, p->dolbyProfile))',
    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->level))',
    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->dolbyVisionProfile))',
    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
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
                'source/common/param.cpp': 'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)\n',
            },
        )
        expect_fail(run_checker(root), 'missing level-idc parse guardrail: function definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
                    '{',
                    '    parsedLevel = (int)(10 * decimalLevel + .5);',
                    '    return true;',
                    '}',
                    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden level-idc parse regression: unbounded fractional rounding')

    print('Level-idc parse safety tests passed')


if __name__ == '__main__':
    main()
