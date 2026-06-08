#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_double_token_safety.py')

# Normalized checker probes used by the coverage scan for double-token guardrails.
NORMALIZED_PROBES = (
    'missing param double token guardrail: function definition',
    'forbidden param double token regression: return !bLocalError;',
    'forbidden param double token regression: ',
    'missing param double token guardrail: ',
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
                'source/common/param.cpp': '\n'.join((
                    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
                    'if (length >= 32)',
                    'std::from_chars_result parsed = std::from_chars(token, token + length, doubleValue);',
                    'if (parsed.ec == std::errc() && parsed.ptr == token + length && std::isfinite(doubleValue))',
                    'value = doubleValue;',
                    'return false;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
                    '{',
                    '    value = x265_atof(number, bLocalError);',
                    '    return !bLocalError;',
                    '}',
                    'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden param double token regression')

    print('Param double token safety tests passed')


if __name__ == '__main__':
    main()
