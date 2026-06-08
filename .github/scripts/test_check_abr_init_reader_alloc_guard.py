#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_init_reader_alloc_guard.py')

# Coverage probe used by the scan for the reviewed ABR Reader allocation guard.
NORMALIZED_PROBES = (
    'PassEncoder::init must guard Reader allocation immediately after construction',
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
                    '{',
                    '    m_reader = new (std::nothrow) Reader(m_id, this);',
                    '    if (!m_reader)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "\\n MALLOC failure in Reader");',
                    '        result = 4;',
                    '        m_ret = 4;',
                    '        return -1;',
                    '    }',
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
                    'if (!(m_cliopt.enableScaler && m_id))',
                    '    m_reader = new Reader(m_id, this);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr init reader alloc guardrail: m_reader = new (std::nothrow) Reader(m_id, this);')

    print('Abr init reader allocation guard tests passed')


if __name__ == '__main__':
    main()
