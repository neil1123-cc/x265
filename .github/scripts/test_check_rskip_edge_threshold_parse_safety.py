#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_rskip_edge_threshold_parse_safety.py')

# Normalized checker probe used by the coverage scan for occurrence-count guardrail failures.
NORMALIZED_PROBES = (
    'missing rskip-edge-threshold guardrail occurrences for : expected at least , found ',
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


def guarded_block():
    return '\n'.join((
        'OPT("rskip-edge-threshold")',
        '{',
        '    bool bEdgeVarThresholdError = false;',
        '    int edgeVarThreshold = parseOptionIntValue(value, bEdgeVarThresholdError);',
        '    bError |= bEdgeVarThresholdError;',
        '    if (!bEdgeVarThresholdError)',
        '        p->edgeVarThreshold = edgeVarThreshold / 100.0f;',
        '}',
    ))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': guarded_block() + '\n' + guarded_block() + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("rskip-edge-threshold") p->edgeVarThreshold = x265_atoi(value, bError) / 100.0f;\n' + guarded_block() + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden rskip-edge-threshold regression: invalid values must not overwrite prior state')

    print('Rskip-edge-threshold parse safety tests passed')


if __name__ == '__main__':
    main()
