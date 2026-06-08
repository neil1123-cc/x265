#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zimg_token_parse_usage.py')

# Coverage probes used by the scan for zimg token parsing guardrails.
# forbidden zimg token parse regression: return end && *end == '\0' && end != number;
# forbidden zimg token parse regression: if (!end || *end != '\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)
# forbidden zimg token parse regression: if (errno == ERANGE || !end || *end != '\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)
NORMALIZED_PROBES = (
    'missing zimg token parse guardrail: #include <cmath>',
    'missing zimg token parse guardrail: #include <cerrno>',
    'expected errno reset in both zimg token parse helpers',
    "forbidden zimg token parse regression: return end && *end == '\\0' && end != number;",
    'forbidden zimg token parse regression: missing finite-value guard',
    "forbidden zimg token parse regression: if (!end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)",
    "forbidden zimg token parse regression: if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)",
    'missing zimg token parse guardrail: ',
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
                'source/filters/zimgfilter.cpp': '\n'.join((
                    '#include <cmath>',
                    '#include <cerrno>',
                    'errno = 0;',
                    'value = std::strtod(number, &end);',
                    "return errno != ERANGE && end && *end == '\\0' && end != number && std::isfinite(value);",
                    'errno = 0;',
                    'long parsed = std::strtol(number, &end, 10);',
                    "if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < 0 || parsed > INT_MAX)",
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/filters/zimgfilter.cpp': "return end && *end == '\\0' && end != number;\n"})
        expect_fail(run_checker(root), 'forbidden zimg token parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/filters/zimgfilter.cpp': '\n'.join((
                    '#include <cmath>',
                    '#include <cerrno>',
                    'errno = 0;',
                    'value = std::strtod(number, &end);',
                    "return errno != ERANGE && end && *end == '\\0' && end != number && std::isfinite(value);",
                    'errno = 0;',
                    'long parsed = std::strtol(number, &end, 10);',
                    "if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)",
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zimg token parse regression')

    print('ZIMG token parse guard tests passed')


if __name__ == '__main__':
    main()
