#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_dither_input_guard.py')

# Coverage probe used by the scan for the reviewed ABR dither input guard.
NORMALIZED_PROBES = (
    'PassEncoder::threadMain must guard null dither input state before x265_dither_image',
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
                    'if (pic_in[view]->bitDepth > m_param->internalBitDepth && m_cliopt.bDither)',
                    '{',
                    '    if (!m_cliopt.input[view])',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing dither input state for view %d in %s\\n",',
                    '            view, profileName);',
                    '        m_ret = 4;',
                    '        goto fail;',
                    '    }',
                    '    x265_dither_image(pic_in[view], m_cliopt.input[view]->getWidth(), m_cliopt.input[view]->getHeight(), errorBuf, m_param->internalBitDepth);',
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
                'source/abrEncApp.cpp': 'x265_dither_image(pic_in[view], m_cliopt.input[view]->getWidth(), m_cliopt.input[view]->getHeight(), errorBuf, m_param->internalBitDepth);\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread dither input guardrail: if (!m_cliopt.input[view])')

    print('ABR thread dither input guard tests passed')


if __name__ == '__main__':
    main()
