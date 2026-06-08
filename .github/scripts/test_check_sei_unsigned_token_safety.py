#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sei_unsigned_token_safety.py')

# Coverage probes used by the scan for SEI unsigned-token guardrails.
NORMALIZED_PROBES = (
    'forbidden SEI unsigned token regression: ',
    'missing SEI unsigned token guardrail: ',
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
                'source/encoder/sei.h': '\n'.join((
                    '#include <cerrno>',
                    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
                    'if (!cursor || !*cursor)',
                    "if (*cursor == '-')",
                    'errno = 0;',
                    'char* end = nullptr;',
                    'unsigned long parsed = std::strtoul(cursor, &end, 10);',
                    'if (errno == ERANGE || end == cursor || parsed > UINT_MAX)',
                    'cursor = end;',
                    'value = (uint32_t)parsed;',
                    'return true;',
                    'static bool consumeSeiLiteral(const char*& cursor, const char* literal)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/sei.h': 'if (end == cursor || parsed > UINT_MAX)\n'})
        expect_fail(run_checker(root), 'forbidden SEI unsigned token regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/sei.h': '\n'.join((
                    '#include <cerrno>',
                    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
                    'if (!cursor || !*cursor)',
                    "if (*cursor == '-')",
                    'errno = 0;',
                    'char* end = nullptr;',
                    'unsigned long parsed = std::strtoul(cursor, &end, 10);',
                    'cursor = end;',
                    'if (errno == ERANGE || end == cursor || parsed > UINT_MAX)',
                    'value = (uint32_t)parsed;',
                    'return true;',
                    'static bool consumeSeiLiteral(const char*& cursor, const char* literal)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'parseSeiUnsignedToken must reject negative, empty, and overflowed tokens before advancing cursor or publishing the parsed value')

    print('SEI unsigned token safety tests passed')


if __name__ == '__main__':
    main()
