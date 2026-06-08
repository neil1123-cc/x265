#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/filters/zimgfilter.cpp')
FORBIDDEN_SNIPPETS = (
    "value = std::strtod(number, &end);",
    "long parsed = std::strtol(number, &end, 10);",
)
REQUIRED_SNIPPETS = (
    '#include <cmath>',
    '#include <cerrno>',
    'errno = 0;',
    "value = std::strtod(number, &end);",
    "return errno != ERANGE && end && *end == '\\0' && end != number && std::isfinite(value);",
    "long parsed = std::strtol(number, &end, 10);",
    "if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < 0 || parsed > INT_MAX)",
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if '#include <cmath>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing zimg token parse guardrail: #include <cmath>'))
    if '#include <cerrno>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing zimg token parse guardrail: #include <cerrno>'))
    if text.count('errno = 0;') < 2:
        failures.append((TARGET.as_posix(), 0, 'expected errno reset in both zimg token parse helpers'))
    for snippet in REQUIRED_SNIPPETS[2:]:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing zimg token parse guardrail: {snippet}'))
    if "return end && *end == '\\0' && end != number;" in text:
        failures.append((TARGET.as_posix(), 0, "forbidden zimg token parse regression: return end && *end == '\\0' && end != number;"))
    if "return errno != ERANGE && end && *end == '\\0' && end != number;" in text:
        failures.append((TARGET.as_posix(), 0, "forbidden zimg token parse regression: missing finite-value guard"))
    if "if (!end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)" in text:
        failures.append((TARGET.as_posix(), 0, "forbidden zimg token parse regression: if (!end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)"))
    if "if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)" in text:
        failures.append((TARGET.as_posix(), 0, "forbidden zimg token parse regression: if (errno == ERANGE || !end || *end != '\\0' || end == number || parsed < INT_MIN || parsed > INT_MAX)"))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zimg token parsing guardrails in zimgfilter.cpp')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('ZIMG token parse usage validated')


if __name__ == '__main__':
    main()
