#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_init_reader_rollback.py')

# Coverage probe used by the scan for the reviewed ABR Reader rollback guard.
NORMALIZED_PROBES = (
    'forbidden abr init reader rollback regression: init must not null out m_reader before destroy() can release it',
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
                    'if (!(m_cliopt.enableScaler && m_id))',
                    '    m_reader = new (std::nothrow) Reader(m_id, this);',
                    'if (!m_encoder)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \\n");',
                    '    rollbackInputHelper();',
                    '    m_ret = 2;',
                    '    if (!result)',
                    '        result = m_ret;',
                    '    return -1;',
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
                    'if (!m_encoder)',
                    '{',
                    '    m_ret = 2;',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr init reader rollback guardrail: if (!(m_cliopt.enableScaler && m_id))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'if (!(m_cliopt.enableScaler && m_id))',
                    '    m_reader = new (std::nothrow) Reader(m_id, this);',
                    'if (!m_encoder)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \\n");',
                    '    m_ret = 2;',
                    '    rollbackInputHelper();',
                    '    if (!result)',
                    '        result = m_ret;',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::init must roll back reader-owned input state before setting the encoder-open failure result and returning')

    print('Abr init reader rollback tests passed')


if __name__ == '__main__':
    main()
