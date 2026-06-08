#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_field_plane_guard.py')

# Coverage probe used by the scan for the reviewed ABR field plane guard.
NORMALIZED_PROBES = (
    'threadMain must guard field plane state before copying field data',
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
                    'if (pic_in[view]->framesize)',
                    '{',
                    '    for (int i = 0; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    '    {',
                    '        if (!pic_in[view]->planes[i] || !picField1.planes[i] || !picField2.planes[i])',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR, "Missing field plane state for view %d plane %d in %s\\n",',
                    '                view, i, profileName);',
                    '            m_ret = 4;',
                    '            goto fail;',
                    '        }',
                    '        char* srcP1 = (char*)pic_in[view]->planes[i];',
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
                    'if (pic_in[view]->framesize)',
                    '{',
                    '    char* srcP1 = (char*)pic_in[view]->planes[i];',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread field-plane guardrail: if (!pic_in[view]->planes[i] || !picField1.planes[i] || !picField2.planes[i])')

    print('ABR thread field-plane guard tests passed')


if __name__ == '__main__':
    main()
