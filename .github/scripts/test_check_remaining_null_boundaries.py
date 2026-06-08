#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_remaining_null_boundaries.py')

# Coverage probes used by the scan for remaining NULL-boundary guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'threadpool NULL handling should stay string-only, not token-based',
    'compat getopt NULL boundary drifted; update allowlist only after review',
    'compat getopt NULL boundary changed; review C compatibility island explicitly',
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


def build_getopt_c():
    lines = ['int line_%d = 0;' % i for i in range(1, 965)]
    replacements = {
        321: 'if (new_str == NULL) {}',
        395: 'nextchar = NULL;',
        411: 'else if (posixly_correct != NULL) {}',
        417: 'if (posixly_correct == NULL) {}',
        422: 'if (__getopt_nonoption_flags == NULL) {}',
        433: 'if (__getopt_nonoption_flags == NULL) {}',
        521: 'optarg = NULL;',
        543: 'if (nextchar == NULL || *nextchar == \'\\0\') {}',
        617: 'if (longopts != NULL) {}',
        635: 'if (longopts != NULL) {}',
        641: 'const struct option *pfound = NULL;',
        664: 'else if (pfound == NULL) {}',
        689: 'if (pfound != NULL) {}',
        737: 'if (longind != NULL) {}',
        752: 'if (my_index(optstring, *nextchar) == NULL) {}',
        782: 'if (temp == NULL || c == \':\') {}',
        802: 'const struct option *pfound = NULL;',
        855: 'else if (pfound == NULL) {}',
        874: 'if (pfound != NULL) {}',
        909: 'if (longind != NULL) {}',
        918: 'nextchar = NULL;',
        932: 'optarg = NULL;',
        933: 'nextchar = NULL;',
        964: 'nextchar = NULL;',
    }
    for line, text in replacements.items():
        lines[line - 1] = text
    return '\n'.join(lines) + '\n'


def build_getopt_h():
    lines = ['int line_%d = 0;' % i for i in range(1, 183)]
    lines[84] = '/* If the field `flag\' is not NULL, it points to a variable that is set */'
    return '\n'.join(lines) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.h': 'static const int ok = 0;\n/* NULL in comment is fine */\n',
                'source/common/threadpool.cpp': 'const char* text = "NULL";\n',
                'source/compat/getopt/getopt.c': build_getopt_c(),
                'source/compat/getopt/getopt.h': build_getopt_h(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.h': 'void* bad = NULL;\n',
                'source/common/threadpool.cpp': 'const char* text = "NULL";\n',
                'source/compat/getopt/getopt.c': build_getopt_c(),
                'source/compat/getopt/getopt.h': build_getopt_h(),
            },
        )
        expect_fail(run_checker(root), 'remove runtime NULL tokens from public header implementations')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.h': 'static const int ok = 0;\n',
                'source/common/threadpool.cpp': 'void* bad = NULL;\n',
                'source/compat/getopt/getopt.c': build_getopt_c(),
                'source/compat/getopt/getopt.h': build_getopt_h(),
            },
        )
        expect_fail(run_checker(root), 'threadpool NULL handling should stay string-only')

    print('Remaining NULL boundary tests passed')


if __name__ == '__main__':
    main()
