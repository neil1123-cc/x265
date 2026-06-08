#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_pools_parse_usage.py')

# Coverage probes used by the scan for SVT pools parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT pools parse regression: ',
    'missing SVT pools parse guardrail: ',
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
                    'if (count > 1)',
                    'else if (count == 1)',
                    "char* separator = std::strchr(pools, ',');",
                    'if (!separator || separator == pools || !separator[1])',
                    "*separator = '\\0';",
                    'temp1 = pools;',
                    'temp2 = separator + 1;',
                    'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
                    'svtHevcParam->targetSocket = 1;',
                    'svtHevcParam->logicalProcessors = logicalProcessors;',
                    'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
                    'svtHevcParam->targetSocket = 0;',
                    'svtHevcParam->logicalProcessors = logicalProcessors;',
                    'free(pools);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': 'temp1 = strtok(pools, ",");\n'})
        expect_fail(run_checker(root), 'forbidden SVT pools parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'if (count > 1)',
                    'else if (count == 1)',
                    "char* separator = std::strchr(pools, ',');",
                    'if (!separator || separator == pools || !separator[1])',
                    'temp1 = pools;',
                    'temp2 = separator + 1;',
                    "*separator = '\\0';",
                    'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
                    'svtHevcParam->targetSocket = 1;',
                    'svtHevcParam->logicalProcessors = logicalProcessors;',
                    'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
                    'svtHevcParam->targetSocket = 0;',
                    'svtHevcParam->logicalProcessors = logicalProcessors;',
                    'free(pools);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT pools parsing must split the two-socket form with the reviewed separator logic and only publish logicalProcessors after the checked integer parse succeeds')

    print('SVT pools parse guard tests passed')


if __name__ == '__main__':
    main()
