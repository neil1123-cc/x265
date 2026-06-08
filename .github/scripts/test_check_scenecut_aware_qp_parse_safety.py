#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scenecut_aware_qp_parse_safety.py')

# Normalized checker probe used by the coverage scan for occurrence-count guardrail failures.
NORMALIZED_PROBES = (
    'missing scenecut-aware-qp guardrail occurrences for : expected at least , found ',
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
        'OPT("scenecut-aware-qp")',
        '{',
        '    bool bSceneCutAwareQpError = false;',
        '    int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);',
        '    bError |= bSceneCutAwareQpError;',
        '    if (!bSceneCutAwareQpError)',
        '        p->bEnableSceneCutAwareQp = sceneCutAwareQp;',
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
                'source/common/param.cpp': 'OPT("scenecut-aware-qp") p->bEnableSceneCutAwareQp = x265_atoi(value, bError);\n' + guarded_block() + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware-qp regression: invalid values must not overwrite prior state')

    print('Scenecut-aware-qp parse safety tests passed')


if __name__ == '__main__':
    main()
