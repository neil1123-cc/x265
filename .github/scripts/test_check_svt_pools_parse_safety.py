#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_pools_parse_safety.py')


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


PASS_SOURCE = '\n'.join((
    'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
    'bError |= bLogicalProcessorsError;',
    'if (!bLogicalProcessorsError)',
    '{',
    '    svtHevcParam->targetSocket = 1;',
    '    svtHevcParam->logicalProcessors = logicalProcessors;',
    '}',
    'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
    'bError |= bLogicalProcessorsError;',
    'if (!bLogicalProcessorsError)',
    '{',
    '    svtHevcParam->targetSocket = 0;',
    '    svtHevcParam->logicalProcessors = logicalProcessors;',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    '                            svtHevcParam->targetSocket = 1;',
                    '                            svtHevcParam->logicalProcessors = x265_atoi(temp2, bLogicalProcessorsError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT pools regression: invalid logical-processor counts must not overwrite target socket state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    '                            svtHevcParam->targetSocket = 1;',
                    '                            svtHevcParam->logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT pools regression: invalid logical-processor counts must not overwrite target socket state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'bError |= bLogicalProcessorsError;',
                    'rememberError(bLogicalProcessorsError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing SVT pools guardrail: logical-processor parse errors must propagate in both socket branches')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'if (!bLogicalProcessorsError)',
                    'if (true)',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing SVT pools guardrail: logical-processor assignments must stay behind both validation branches')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '    svtHevcParam->logicalProcessors = logicalProcessors;',
                    '    svtHevcParam->logicalProcessors = otherProcessors;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing SVT pools guardrail: validated logical-processor counts must be assigned in both socket branches')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '    svtHevcParam->targetSocket = 1;\n'
                    '    svtHevcParam->logicalProcessors = logicalProcessors;',
                    '    svtHevcParam->logicalProcessors = logicalProcessors;\n'
                    '    svtHevcParam->targetSocket = 1;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'SVT pools temp2 branch must validate logical-processor counts before updating socket state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '    svtHevcParam->targetSocket = 0;\n'
                    '    svtHevcParam->logicalProcessors = logicalProcessors;',
                    '    svtHevcParam->logicalProcessors = logicalProcessors;\n'
                    '    svtHevcParam->targetSocket = 0;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'SVT pools temp1 branch must validate logical-processor counts before updating socket state')

    print('SVT pools parse safety tests passed')


if __name__ == '__main__':
    main()
