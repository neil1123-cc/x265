#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_multiview_field_guard.py')

# Coverage probes used by the scan for ABR multiview-field guardrails.
NORMALIZED_PROBES = (
    'threadMain must reject multiview field mode before shared field pictures reach encode submission',
    'missing ABR multiview-field guardrail: ',
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
                    'if (m_param->numViews > 1 && m_param->bField && m_param->interlaceMode)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Multiview field/interlace encoding is not supported in %s\\n",',
                    '        profileName);',
                    '    m_ret = 4;',
                    '    goto fail;',
                    '}',
                    'picInput = *pic_in ? (inputNum ? &picField2 : &picField1) : nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'picInput = *pic_in ? (inputNum ? &picField2 : &picField1) : nullptr;\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR multiview-field guardrail')

    print('ABR multiview field guard tests passed')


if __name__ == '__main__':
    main()
