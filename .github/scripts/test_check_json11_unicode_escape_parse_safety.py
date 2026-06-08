#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_json11_unicode_escape_parse_safety.py')

# Normalized checker probe used by the coverage scan for escaped guardrail failures.
NORMALIZED_PROBES = (
    'missing json11 unicode escape guardrail: bad \\u escape: ',
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
    'static inline int decode_hex_digit(char ch) {',
    "    if (in_range(ch, '0', '9'))",
    "        return ch - '0';",
    "    if (in_range(ch, 'a', 'f'))",
    "        return ch - 'a' + 10;",
    "    return ch - 'A' + 10;",
    '}',
    'string parse_string() {',
    '    string esc = str.substr(i, 4);',
    '    if (esc.length() < 4) {',
    '        return fail("bad \\\\u escape: " + esc, "");',
    '    }',
    '    for (int j = 0; j < 4; j++) {',
    "        if (!in_range(esc[j], 'a', 'f') && !in_range(esc[j], 'A', 'F')",
    "                && !in_range(esc[j], '0', '9'))",
    '            return fail("bad \\\\u escape: " + esc, "");',
    '    }',
    '    long codepoint = 0;',
    '    for (int j = 0; j < 4; j++)',
    '        codepoint = (codepoint << 4) | decode_hex_digit(esc[j]);',
    '    if (in_range(last_escaped_codepoint, 0xD800, 0xDBFF)',
    '            && in_range(codepoint, 0xDC00, 0xDFFF)) {',
    '    }',
    '    i += 4;',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/dynamicHDR10/json11/json11.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join((
                    'string parse_string() {',
                    '    string esc = str.substr(i, 4);',
                    '    long codepoint = strtol(esc.data(), nullptr, 16);',
                    '    i += 4;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden json11 unicode escape regression: long codepoint = strtol(esc.data(), nullptr, 16);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/json11/json11.cpp': PASS_SOURCE.replace(
                    '        return fail("bad \\\\u escape: " + esc, "");\n',
                    '',
                    2,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing json11 unicode escape guardrail: bad \\\\u escape: ')

    print('json11 unicode escape parse safety tests passed')


if __name__ == '__main__':
    main()
