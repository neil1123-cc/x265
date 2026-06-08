#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_deblock_parse_usage.py')

# Coverage probes used by the scan for SVT deblock parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT deblock parse regression: ',
    'missing SVT deblock parse guardrail: ',
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
                    'OPT("deblock")',
                    'bool bDeblockValueError = false;',
                    'int deblockValue = parseOptionIntValue(value, bDeblockValueError);',
                    'if (!bDeblockValueError)',
                    'svtHevcParam->disableDlfFlag = deblockValue ? 0 : 1;',
                    'else',
                    'int deblockEnabled = x265_atobool(value, bError);',
                    'if (!bError)',
                    'svtHevcParam->disableDlfFlag = deblockEnabled ? 0 : 1;',
                    'OPT("sao")',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': 'if (strtol(value, nullptr, 0))\n'})
        expect_fail(run_checker(root), 'forbidden SVT deblock parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("deblock")',
                    'int deblockEnabled = x265_atobool(value, bError);',
                    'if (!bError)',
                    'svtHevcParam->disableDlfFlag = deblockEnabled ? 0 : 1;',
                    'bool bDeblockValueError = false;',
                    'int deblockValue = parseOptionIntValue(value, bDeblockValueError);',
                    'if (!bDeblockValueError)',
                    'svtHevcParam->disableDlfFlag = deblockValue ? 0 : 1;',
                    'else',
                    'OPT("sao")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT deblock parsing must preserve the reviewed integer-first parse path before the boolean fallback mutates disableDlfFlag')

    print('SVT deblock parse guard tests passed')


if __name__ == '__main__':
    main()
