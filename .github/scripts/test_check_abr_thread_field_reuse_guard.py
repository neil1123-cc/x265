#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_field_reuse_guard.py')

# Coverage probes used by the scan for ABR field reuse guardrails.
NORMALIZED_PROBES = (
    'threadMain must validate reused field-buffer metadata and stride before copying field data',
    'missing ABR field-reuse guardrail: ',
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
                    'fieldBuffersCreated = true;',
                    'else if (picField1.bitDepth != pic_in[view]->bitDepth ||',
                    '    picField1.colorSpace != pic_in[view]->colorSpace ||',
                    '    picField1.height != (pic_in[view]->height >> 1) ||',
                    '    picField1.framesize != (pic_in[view]->framesize >> 1))',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer metadata for view %d in %s\\n",',
                    '        view, profileName);',
                    '    m_ret = 4;',
                    '    goto fail;',
                    '}',
                    'else',
                    '{',
                    '    for (int i = 0; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)',
                    '    {',
                    '        if (picField1.stride[i] != pic_in[view]->stride[i] || picField2.stride[i] != pic_in[view]->stride[i])',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer stride for view %d plane %d in %s\\n",',
                    '                view, i, profileName);',
                    '            m_ret = 4;',
                    '            goto fail;',
                    '        }',
                    '    }',
                    '}',
                    'picField1.pts = picField1.poc = pic_in[view]->poc;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'fieldBuffersCreated = true;\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR field-reuse guardrail')

    print('ABR field-reuse guard tests passed')


if __name__ == '__main__':
    main()
