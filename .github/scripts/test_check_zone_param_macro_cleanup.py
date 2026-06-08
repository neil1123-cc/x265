#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zone_param_macro_cleanup.py')

# Coverage probes used by the scan for zone param macro-cleanup guardrails.
NORMALIZED_PROBES = (
    'missing zone param parser',
    'missing zone param cleanup guardrail: OPT("fast-intra") p->bEnableFastIntra = x265_atobool(value, bError);',
    'forbidden zone param macro regression: #define atoi(str) x265_atoi(str, bError)',
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
                'source/common/param.cpp': '\n'.join((
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("fast-intra") p->bEnableFastIntra = x265_atobool(value, bError);',
                    '    OPT("tskip-fast") p->bEnableTSkipFast = x265_atobool(value, bError);',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    '/* internal versions of string-to-int with additional error checking */',
                    '#undef atoi',
                    '#undef atof',
                    '#define atoi(str) x265_atoi(str, bError)',
                    '#define atof(str) x265_atof(str, bError)',
                    '#define atobool(str) (x265_atobool(str, bError))',
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("fast-intra") p->bEnableFastIntra = atobool(value);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zone param macro regression')

    print('zone param macro cleanup tests passed')


if __name__ == '__main__':
    main()
