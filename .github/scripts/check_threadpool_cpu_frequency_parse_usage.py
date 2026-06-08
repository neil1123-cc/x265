#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/threadpool.cpp')
FORBIDDEN_SNIPPETS = (
    'double mhz = std::strtod(line.c_str() + colon + 1, nullptr);',
    'double mhz = atof(line.c_str() + colon + 1);',
    'double mhz = std::atof(line.c_str() + colon + 1);',
)
REQUIRED_SNIPPETS = (
    'double getCPUFrequencyMHz()',
    'static bool parseThreadPoolCpuMhzValue(const char* value, double& mhz)',
    'std::ifstream f("/proc/cpuinfo");',
    'if (line.find("cpu MHz") != std::string::npos)',
    "size_t colon = line.find(':');",
    'const char* value = line.c_str() + colon + 1;',
    'errno = 0;',
    'char* end = nullptr;',
    'mhz = std::strtod(value, &end);',
    'while (end && *end && std::isspace(static_cast<unsigned char>(*end)))',
    'double mhz = 0.0;',
    'if (parseThreadPoolCpuMhzValue(value, mhz) && mhz > maxMhz)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if '#include <cerrno>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing threadpool CPU frequency guardrail: #include <cerrno>'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden threadpool CPU frequency parse regression: {snippet}'))
    if 'if (end != value && std::isfinite(mhz) && mhz > maxMhz)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden threadpool CPU frequency parse regression: missing ERANGE guard'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing threadpool CPU frequency guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check threadpool CPU frequency parsing guardrails')
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

    print('Threadpool CPU frequency parse usage validated')


if __name__ == '__main__':
    main()
