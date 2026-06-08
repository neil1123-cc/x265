#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_rdpenalty_parse_safety.py')

# Normalized checker probe used by the coverage scan for counted guardrail failures.
NORMALIZED_PROBES = (
    'missing rdpenalty guardrail (/): ',
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
                    'OPT("rdpenalty")',
                    '{',
                    '    bool bRdPenaltyError = false;',
                    '    int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);',
                    '    bError |= bRdPenaltyError;',
                    '    if (!bRdPenaltyError)',
                    '        p->rdPenalty = rdPenalty;',
                    '}',
                    'OPT("rdpenalty")',
                    '{',
                    '    bool bRdPenaltyError = false;',
                    '    int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);',
                    '    bError |= bRdPenaltyError;',
                    '    if (!bRdPenaltyError)',
                    '        p->rdPenalty = rdPenalty;',
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
                    'OPT("rdpenalty")',
                    '{',
                    '    bool bRdPenaltyError = false;',
                    '    int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);',
                    '    bError |= bRdPenaltyError;',
                    '    if (!bRdPenaltyError)',
                    '        p->rdPenalty = rdPenalty;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing rdpenalty guardrail (1/2): OPT("rdpenalty")')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("rdpenalty") p->rdPenalty = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden rdpenalty regression: invalid values must not overwrite prior state')

    print('RDPenalty parse safety tests passed')


if __name__ == '__main__':
    main()
