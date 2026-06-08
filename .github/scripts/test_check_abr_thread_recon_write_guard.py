#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_recon_write_guard.py')

# Coverage probes used by the scan for ABR recon-write guardrails.
NORMALIZED_PROBES = (
    'threadMain must check recon output write results before continuing',
    'missing ABR recon-write guardrail: ',
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
                    'if (!reconPlay->writePicture(*pic_recon))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Failed recon playback output for encoder %u\\n", m_id);',
                    '    m_ret = 4;',
                    '    goto fail;',
                    '}',
                    'if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Failed layered recon output for encoder %u layer %d\\n", m_id, layer);',
                    '    m_ret = 4;',
                    '    goto fail;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'reconPlay->writePicture(*pic_recon);\n'})
        expect_fail(run_checker(root), 'missing ABR recon-write guardrail')

    print('ABR recon write guard tests passed')


if __name__ == '__main__':
    main()
