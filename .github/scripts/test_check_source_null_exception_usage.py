#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_source_null_exception_usage.py')

# Coverage probes used by the scan for source NULL exception guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'remove legacy internal NULL macro from common header: ',
    'limit remaining NULL usage to reviewed compatibility macro and string-token exception sites',
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
                'source/common/common.h': 'static const int ok = 1;\n',
                'source/common/threadpool.cpp': '\n'.join(
                    (
                        'if (std::strcmp(p->numaPools, "NULL") == 0) {}',
                        'else if (!strcasecmp(nodeStr, "NULL")) {}',
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
                'source/common/common.h': '#ifndef NULL\n#define NULL 0\n',
                'source/common/threadpool.cpp': 'if (std::strcmp(p->numaPools, "NULL") == 0) {}\n',
            },
        )
        expect_fail(run_checker(root), 'remove legacy internal NULL macro from common header')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/common.h': '// NULL in comment is fine\nconst char* text = "NULL";\n',
                'source/common/threadpool.cpp': '/* NULL in comment is fine */\nconst char* text = "NULL";\n',
            },
        )
        expect_pass(run_checker(root))

    print('Source NULL exception guard tests passed')


if __name__ == '__main__':
    main()
