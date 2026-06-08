#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadpool_cpu_frequency_parse_usage.py')

# Coverage probes used by the scan for threadpool CPU-frequency parsing guardrails.
NORMALIZED_PROBES = (
    'missing threadpool CPU frequency guardrail: #include <cerrno>',
    'forbidden threadpool CPU frequency parse regression: missing ERANGE guard',
    'forbidden threadpool CPU frequency parse regression: ',
    'missing threadpool CPU frequency guardrail: ',
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
                'source/common/threadpool.cpp': '\n'.join((
                    'double getCPUFrequencyMHz()',
                    'static bool parseThreadPoolCpuMhzValue(const char* value, double& mhz)',
                    '#include <cerrno>',
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
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/threadpool.cpp': 'double mhz = std::strtod(line.c_str() + colon + 1, nullptr);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden threadpool CPU frequency parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/threadpool.cpp': 'double getCPUFrequencyMHz()\n',
            },
        )
        expect_fail(run_checker(root), 'missing threadpool CPU frequency guardrail')

    print('Threadpool CPU frequency parse guard tests passed')


if __name__ == '__main__':
    main()
