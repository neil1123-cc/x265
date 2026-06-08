#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_dynamic_hdr10_legacy_patterns.py')

# Coverage probes used by the scan for dynamic HDR10 legacy-pattern guardrails.
NORMALIZED_PROBES = (
    'missing file',
)

TARGETS = (
    'source/dynamicHDR10/JsonHelper.cpp',
    'source/dynamicHDR10/JsonHelper.h',
    'source/dynamicHDR10/metadataFromJson.cpp',
    'source/dynamicHDR10/metadataFromJson.h',
    'source/dynamicHDR10/SeiMetadataDictionary.cpp',
    'source/dynamicHDR10/SeiMetadataDictionary.h',
    'source/dynamicHDR10/BasicStructures.h',
    'source/dynamicHDR10/api.cpp',
    'source/dynamicHDR10/hdr10plus.h',
    'source/dynamicHDR10/json11/json11.cpp',
    'source/dynamicHDR10/json11/json11.h',
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
                'source/dynamicHDR10/json11/json11.h': '\n'.join(
                    (
                        '#define JSON11_NOEXCEPT noexcept',
                        '#ifndef snprintf',
                        '#define snprintf _snprintf_s',
                        '#endif',
                        '// NULL in comment is fine',
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
                'source/dynamicHDR10/JsonHelper.cpp': 'void* bad = NULL;\n',
            },
        )
        expect_fail(run_checker(root), 'avoid GNU++20 legacy pattern in dynamicHDR10 sources: NULL')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/metadataFromJson.cpp': 'void f() throw() {}\n',
            },
        )
        expect_fail(run_checker(root), 'avoid GNU++20 legacy pattern in dynamicHDR10 sources: throw()')

    print('dynamicHDR10 legacy pattern tests passed')


if __name__ == '__main__':
    main()
