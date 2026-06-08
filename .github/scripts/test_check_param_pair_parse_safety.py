#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_pair_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing pair parse guardrail: ',
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


PASS_SOURCE = '\n'.join((
    'static bool splitOptionPair(const char* value, char separatorChar,',
    'if (!value)',
    'const char* separator = std::strchr(value, separatorChar);',
    'if (!separator)',
    'firstToken = value;',
    'firstLength = (size_t)(separator - value);',
    'secondToken = separator + 1;',
    'secondLength = std::strlen(secondToken);',
    'return firstLength && secondLength;',
    'static uint8_t parseOptionUint8Token(const char* token, size_t tokenLength, bool& bError)',
    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
    'if (!splitOptionPair(value, separatorChar, firstToken, firstLength, secondToken, secondLength))',
    'int parsedFirst = parseOptionIntToken(firstToken, firstLength, bLocalError);',
    'int parsedSecond = parseOptionIntToken(secondToken, secondLength, bLocalError);',
    'if (bLocalError)',
    'first = parsedFirst;',
    'second = parsedSecond;',
    'static bool parseOptionUintPair(const char* value, char separatorChar, uint32_t& first, uint32_t& second)',
    'if (!parseOptionIntPair(value, separatorChar, parsedFirst, parsedSecond) || parsedFirst < 0 || parsedSecond < 0)',
    'static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)',
    'int parsedThird = parseOptionIntToken(parts[2], lengths[2], bLocalError);',
    'int parsedFourth = parseOptionIntToken(parts[3], lengths[3], bLocalError);',
    'third = parsedThird;',
    'fourth = parsedFourth;',
    'static bool parseOptionDoubleToken(const char* token, size_t tokenLength, double& value)',
    "bError |= !parseOptionIntPair(value, 'x', p->sourceWidth, p->sourceHeight);",
    "if (!parseOptionIntPair(value, 'x', sourceWidth, sourceHeight))",
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
                    'static bool splitOptionPair(const char* value, char separatorChar,',
                    'static bool splitSomethingElse(const char* value, char separatorChar,',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing pair helper definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'return firstLength && secondLength;',
                    'return true;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden pair parse regression: missing empty-side guard')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'first = parsedFirst;',
                    'first = parseOptionIntToken(firstToken, firstLength, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden pair parse regression: direct pair helper writes')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'if (!parseOptionIntPair(value, separatorChar, parsedFirst, parsedSecond) || parsedFirst < 0 || parsedSecond < 0)',
                    'if (!parseOptionIntPair(value, separatorChar, parsedFirst, parsedSecond))',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden uint pair regression: missing negative-value guard')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)',
                    'static bool parseOptionQuad(const char* value, int& first, int& second, int& third, int& fourth)',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing quad helper definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'third = parsedThird;',
                    'third = parseOptionIntToken(parts[2], lengths[2], bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden quad parse regression: direct quad helper writes')

    print('Pair parse helper safety tests passed')


if __name__ == '__main__':
    main()
