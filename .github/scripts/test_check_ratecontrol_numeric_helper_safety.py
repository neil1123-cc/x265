#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_numeric_helper_safety.py')

# Coverage probes used by the scan for ratecontrol numeric helper guardrails.
NORMALIZED_PROBES = (
    'expected errno reset in all reviewed ratecontrol numeric parse helpers',
    'forbidden ratecontrol numeric helper regression: ',
    'missing ratecontrol numeric helper guardrail: ',
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
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    '#include <cerrno>',
                    'errno = 0;',
                    'errno = 0;',
                    'errno = 0;',
                    "if (*cursor == '-')",
                    'if (errno == ERANGE || end == cursor || parsedFirst > UINT_MAX || *end != separator)',
                    "if (errno == ERANGE || end == cursor || parsedSecond > UINT_MAX || (*end != ' ' && *end != '\\0'))",
                    'double parsed = std::strtod(token, &end);',
                    "if (errno == ERANGE || !end || *end != '\\0' || end == token || !std::isfinite(parsed))",
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/ratecontrol.cpp': "if (end == cursor || parsedFirst > UINT_MAX || *end != separator)\n"})
        expect_fail(run_checker(root), 'forbidden ratecontrol numeric helper regression')

    print('Ratecontrol numeric helper safety tests passed')


if __name__ == '__main__':
    main()
