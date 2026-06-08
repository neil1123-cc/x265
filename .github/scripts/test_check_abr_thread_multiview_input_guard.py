#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_multiview_input_guard.py')

# Coverage probes used by the scan for ABR multiview input guardrails.
NORMALIZED_PROBES = (
    'threadMain must validate multiview input parity before encode submission',
    'missing ABR multiview input guardrail: ',
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
                    'if (m_param->numViews > 1)',
                    '{',
                    '    bool hasPrimaryView = pic_in[0] != nullptr;',
                    '    for (int view = 1; view < viewCount; view++)',
                    '    {',
                    '        if (hasPrimaryView != (pic_in[view] != nullptr))',
                    '        {',
                    '            x265_log(m_param, X265_LOG_ERROR, "Mismatched multiview input state for view %d in %s\\n",',
                    '                view, profileName);',
                    '            m_ret = 4;',
                    '            goto fail;',
                    '        }',
                    '    }',
                    '}',
                    'if (inputPicNum == 2)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'if (inputPicNum == 2)\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR multiview input guardrail')

    print('ABR multiview input guard tests passed')


if __name__ == '__main__':
    main()
