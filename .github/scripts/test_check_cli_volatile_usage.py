#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_volatile_usage.py')


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
        expect_fail(run_checker(root), 'missing file')

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
                'source/abrEncApp.cpp': 'static volatile int bad_flag = 0;\n',
                'source/common/cpu.cpp': 'static volatile sig_atomic_t canjump = 0;\n',
                'source/common/threading.h': '#define ATOMIC_INC(ptr) InterlockedIncrement((volatile LONG*)ptr)\n',
            },
        )
        expect_fail(run_checker(root), 'limit volatile usage to reviewed GNU++20 signal-handler and Windows API boundary sites')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '// volatile in comment is fine\n',
                'source/common/cpu.cpp': 'const char* text = "volatile";\n',
                'source/common/threading.h': '/* volatile in comment is fine */\n',
            },
        )
        expect_pass(run_checker(root))

    print('CLI volatile guard tests passed')


if __name__ == '__main__':
    main()
