#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_json11_number_boundary_safety.py')

# Coverage probes used by the scan for json11 number-boundary guardrails.
NORMALIZED_PROBES = (
    'missing json11 number boundary guardrail: ',
    'forbidden json11 number boundary regression: ',
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
                    'Json parse_number() {',
                    '    size_t start_pos = i;',
                    '    auto current = [this]() -> char {',
                    "        return i < str.size() ? str[i] : '\\0';",
                    '    };',
                    '    char ch = current();',
                    "    if (ch == '-') {",
                    '        i++;',
                    '        ch = current();',
                    '    }',
                    "    if (ch == '0') {",
                    '        i++;',
                    '        ch = current();',
                    "        if (in_range(ch, '0', '9'))",
                    '            return fail("leading 0s not permitted in numbers");',
                    "    } else if (in_range(ch, '1', '9')) {",
                    '        i++;',
                    '        ch = current();',
                    "        while (in_range(ch, '0', '9')) {",
                    '            i++;',
                    '            ch = current();',
                    '        }',
                    '    } else {',
                    '        return fail("invalid " + esc(ch) + " in number");',
                    '    }',
                    "    if (ch != '.' && ch != 'e' && ch != 'E'",
                    '            && (i - start_pos) <= static_cast<size_t>(std::numeric_limits<int>::digits10)) {',
                    '        return static_cast<int>(std::strtol(str.c_str() + start_pos, nullptr, 10));',
                    '    }',
                    "    if (ch == '.') {",
                    '        i++;',
                    '        ch = current();',
                    "        if (!in_range(ch, '0', '9'))",
                    '            return fail("at least one digit required in fractional part");',
                    "        while (in_range(ch, '0', '9')) {",
                    '            i++;',
                    '            ch = current();',
                    '        }',
                    '    }',
                    "    if (ch == 'e' || ch == 'E') {",
                    '        i++;',
                    '        ch = current();',
                    "        if (ch == '+' || ch == '-') {",
                    '            i++;',
                    '            ch = current();',
                    '        }',
                    "        if (!in_range(ch, '0', '9'))",
                    '            return fail("at least one digit required in exponent");',
                    "        while (in_range(ch, '0', '9')) {",
                    '            i++;',
                    '            ch = current();',
                    '        }',
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
                    "    if (str[i] == '-')",
                    '        i++;',
                    "    if (str[i] == '0') {",
                    '        i++;',
                    "        if (in_range(str[i], '0', '9'))",
                    '            return fail("leading 0s not permitted in numbers");',
                    '    }',
                    '    return Json();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden json11 number boundary regression')

    print('json11 number boundary safety tests passed')


if __name__ == '__main__':
    main()
