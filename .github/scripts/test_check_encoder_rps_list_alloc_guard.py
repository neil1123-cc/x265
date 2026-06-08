#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_rps_list_alloc_guard.py')

# Coverage probe used by the scan for the reviewed RPS list allocation cleanup guard.
NORMALIZED_PROBES = (
    'Encoder::computeSPSRPSIndex must route RPSListNode allocation failures through fail cleanup',
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


def valid_text():
    return '\n'.join((
        'RPSListNode* newIdxNode = new (std::nothrow) RPSListNode();',
        'if (newIdxNode == nullptr)',
        '    goto fail;',
        'fail:',
        'delete freeIndex;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('RPSListNode* newIdxNode = new (std::nothrow) RPSListNode();', 'RPSListNode* newIdxNode = new RPSListNode();', 1)})
        expect_fail(run_checker(root), 'forbidden encoder RPS-list allocation regression: RPSListNode* newIdxNode = new RPSListNode();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('    goto fail;\n', '', 1)})
        expect_fail(run_checker(root), 'missing encoder RPS-list allocation guardrail: goto fail;')

    print('Encoder RPS-list allocation guard tests passed')


if __name__ == '__main__':
    main()
