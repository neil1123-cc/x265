#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_json11_noexcept_usage.py')

# Coverage probes used by the scan for json11 noexcept guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'avoid old-style throw() exception specifications in json11 header',
    'avoid old-style throw() exception specifications in json11 source',
    'avoid redefining noexcept directly in json11 compatibility layer: ',
    'missing json11 noexcept compatibility token: ',
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
                'source/dynamicHDR10/json11/json11.h': '\n'.join(
                    (
                        'class Json {',
                        'public:',
                        '    Json() noexcept;',
                        '    Json(std::nullptr_t) noexcept;',
                        '};',
                    )
                ) + '\n',
                'source/dynamicHDR10/json11/json11.cpp': '\n'.join(
                    (
                        'Json::Json() noexcept {}',
                        'Json::Json(std::nullptr_t) noexcept {}',
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
                'source/dynamicHDR10/json11/json11.h': '#define JSON11_NOEXCEPT throw()\n',
                'source/dynamicHDR10/json11/json11.cpp': 'Json::Json() throw() {}\n',
            },
        )
        expect_fail(run_checker(root), 'avoid old-style throw() exception specifications')

    print('json11 noexcept guard tests passed')


if __name__ == '__main__':
    main()
