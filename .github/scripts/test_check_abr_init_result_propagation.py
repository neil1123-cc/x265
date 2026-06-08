#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_init_result_propagation.py')

# Coverage probe used by the scan for the reviewed ABR init result propagation.
NORMALIZED_PROBES = (
    'PassEncoder::init must propagate result on late failure path ',
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
    valid_text = '\n'.join((
        'if (!m_cliopt.parseZoneFile())',
        '{',
        '    m_ret = 1;',
        '    if (!result)',
        '        result = m_ret;',
        '    return -1;',
        '}',
        'if (i->isFail())',
        '{',
        '    m_ret = 4;',
        '    if (!result)',
        '        result = m_ret;',
        '    return -1;',
        '}',
        'if (m_cliopt.output->isFail())',
        '{',
        '    m_ret = 3;',
        '    if (!result)',
        '        result = m_ret;',
        '    return -1;',
        '}',
        'if (!m_encoder)',
        '{',
        '    m_ret = 2;',
        '    if (!result)',
        '        result = m_ret;',
        '    return -1;',
        '}',
    )) + '\n'

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': valid_text})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'if (!m_encoder)\n{\n    m_ret = 2;\n    return -1;\n}\n'})
        expect_fail(run_checker(root), 'missing abr init result propagation guardrail: if (!result)')

    print('Abr init result propagation tests passed')


if __name__ == '__main__':
    main()
