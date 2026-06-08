#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_json11_short_int_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing json11 short-int guardrail: ',
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
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join((
                    '#include <charconv>',
                    'static inline bool parse_short_json_int(const char* begin, const char* end, int& value) {',
                    '    std::from_chars_result parsed = std::from_chars(begin, end, value);',
                    '    return parsed.ec == std::errc() && parsed.ptr == end;',
                    '}',
                    'Json parse_number() {',
                    "    if (ch != '.' && ch != 'e' && ch != 'E'",
                    '            && (i - start_pos) <= static_cast<size_t>(std::numeric_limits<int>::digits10)) {',
                    '        int intValue = 0;',
                    '        if (parse_short_json_int(str.c_str() + start_pos, str.c_str() + i, intValue))',
                    '            return intValue;',
                    '    }',
                    '    return std::strtod(str.c_str() + start_pos, nullptr);',
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
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join((
                    'Json parse_number() {',
                    '    return static_cast<int>(std::strtol(str.c_str() + start_pos, nullptr, 10));',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden json11 short-int regression: return static_cast<int>(std::strtol(str.c_str() + start_pos, nullptr, 10));')

    print('json11 short integer parse safety tests passed')


if __name__ == '__main__':
    main()
