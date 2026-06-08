#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadpool_cpu_frequency_tail_guard.py')

# Coverage probes used by the scan for threadpool CPU-frequency tail guardrails.
NORMALIZED_PROBES = (
    'threadpool CPU frequency parser must trim trailing whitespace before accepting the parsed value',
    'missing threadpool CPU frequency tail guardrail: ',
    'forbidden threadpool CPU frequency tail regression: ',
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
                    '#include <cctype>',
                    'char* end = nullptr;',
                    'while (end && *end && std::isspace(static_cast<unsigned char>(*end)))',
                    '    ++end;',
                    "return errno != ERANGE && end != value && end && *end == '\\0' && std::isfinite(mhz);",
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
                'source/common/threadpool.cpp': '\n'.join((
                    '#include <cctype>',
                    'char* end = nullptr;',
                    'if (errno != ERANGE && end != value && std::isfinite(mhz) && mhz > maxMhz)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden threadpool CPU frequency tail regression')

    print('Threadpool CPU frequency tail guard tests passed')


if __name__ == '__main__':
    main()
