#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_source_legacy_patterns.py')

# Coverage probes used by the scan for source legacy-pattern guardrails.
NORMALIZED_PROBES = (
    'missing file',
)

TARGETS = (
    'source/abrEncApp.cpp',
    'source/common/common.cpp',
    'source/common/common.h',
    'source/common/cpu.cpp',
    'source/common/threading.h',
    'source/common/threadpool.cpp',
    'source/encoder/encoder.cpp',
    'source/x265.cpp',
    'source/x265.h',
    'source/x265cli.cpp',
    'source/x265cli.h',
)


def write_targets(root, contents):
    for relative in TARGETS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents.get(relative, 'int ok = 0;\n'))


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
                'source/abrEncApp.cpp': 'static volatile sig_atomic_t b_ctrl_c /* = 0 */;\n',
                'source/common/cpu.cpp': 'static volatile sig_atomic_t canjump = 0;\n',
                'source/common/threading.h': '\n'.join(
                    (
                        '#define ATOMIC_INC(ptr)       InterlockedIncrement((volatile LONG*)ptr)',
                        '#define ATOMIC_DEC(ptr)       InterlockedDecrement((volatile LONG*)ptr)',
                        '#define ATOMIC_ADD(ptr, val)  (sizeof(*(ptr)) == 8 ? \\',
                        '                               InterlockedExchangeAdd64((volatile LONGLONG*)ptr, (LONGLONG)(val)) : \\',
                        '                               InterlockedExchangeAdd((volatile LONG*)ptr, (LONG)(val)))',
                        '#define ATOMIC_OR(ptr, mask)  _InterlockedOr((volatile LONG*)ptr, (LONG)mask)',
                        '#define ATOMIC_AND(ptr, mask) _InterlockedAnd((volatile LONG*)ptr, (LONG)mask)',
                    )
                ) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'void* bad = NULL;\n',
            },
        )
        expect_fail(run_checker(root), 'avoid legacy GNU++20-sensitive token in core C/C++ sources: NULL')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'void f() throw() {}\n',
            },
        )
        expect_fail(run_checker(root), 'avoid legacy GNU++20-sensitive token in core C/C++ sources: throw()')

    print('Core source legacy pattern tests passed')


if __name__ == '__main__':
    main()
