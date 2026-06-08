#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_api_null_guard.py')

# Coverage probe used by the scan for the reviewed ABR thread API guard.
NORMALIZED_PROBES = (
    'PassEncoder::threadMain must guard null api before dereferencing it',
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
                    'const x265_api* api = m_cliopt.api;',
                    'if (!api)',
                    '{',
                    '    m_ret = 2;',
                    '    m_threadActive.store(false);',
                    '    m_parent->m_numActiveEncodes.decr();',
                    '    return;',
                    '}',
                    'if (api->encoder_headers(m_encoder, &p_nal, &nal) < 0)',
                    '{',
                    '}',
                    'api->picture_init(m_param, &picField1);',
                    'int numEncoded = api->encoder_encode(m_encoder, &p_nal, &nal, picInput, pic_recon);',
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
                    'const x265_api* api = m_cliopt.api;',
                    'if (api->encoder_headers(m_encoder, &p_nal, &nal) < 0)',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread api null guardrail: if (!api)')

    print('ABR thread api null guard tests passed')


if __name__ == '__main__':
    main()
