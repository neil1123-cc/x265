#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_init_helper_cleanup.py')

# Coverage probe used by the scan for the reviewed ABR init rollback helper.
NORMALIZED_PROBES = (
    'PassEncoder::init must call rollbackInputHelper() before returning from ',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'auto rollbackInputHelper = [&]()',
                    '{',
                    '    if (m_reader)',
                    '    {',
                    '        delete m_reader;',
                    '        m_reader = nullptr;',
                    '    }',
                    '    else if (m_scaler)',
                    '    {',
                    '        m_scaler->destroy();',
                    '        delete m_scaler;',
                    '        m_scaler = nullptr;',
                    '    }',
                    '}',
                    'if (!m_cliopt.parseZoneFile())',
                    '{',
                    '    rollbackInputHelper();',
                    '}',
                    'if (i->isFail())',
                    '{',
                    '    rollbackInputHelper();',
                    '}',
                    'if (m_cliopt.output->isFail())',
                    '{',
                    '    rollbackInputHelper();',
                    '}',
                    'if (!m_encoder)',
                    '{',
                    '    rollbackInputHelper();',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'if (!m_cliopt.parseZoneFile())',
                    '{',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr init helper cleanup guardrail: auto rollbackInputHelper = [&]()')

    print('Abr init helper cleanup tests passed')


if __name__ == '__main__':
    main()
