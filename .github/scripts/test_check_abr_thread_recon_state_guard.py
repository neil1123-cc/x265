#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_recon_state_guard.py')

# Coverage probe used by the scan for the reviewed ABR recon state guard.
NORMALIZED_PROBES = (
    'threadMain must guard recon/save state before dereferencing pic_recon',
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
                    'if (reconPlay && numEncoded)',
                    '{',
                    '    if (!pic_recon)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing recon output state for encoder %u\\n", m_id);',
                    '    }',
                    '    if (!reconPlay->writePicture(*pic_recon))',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Failed recon playback output for encoder %u\\n", m_id);',
                    '    }',
                    '}',
                    'if (isAbrSave && numEncoded)',
                    '{',
                    '    if (!pic_recon)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing analysis save state for encoder %u\\n", m_id);',
                    '    }',
                    '    copyInfo(analysisInfo);',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'if (!reconPlay->writePicture(*pic_recon))\n{\n}\n'})
        expect_fail(run_checker(root), 'missing ABR thread recon-state guardrail: if (reconPlay && numEncoded)')

    print('ABR thread recon-state guard tests passed')


if __name__ == '__main__':
    main()
