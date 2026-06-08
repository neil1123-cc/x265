#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_pic_in_reset_guard.py')

# Coverage probes used by the scan for ABR pic_in reset guardrails.
NORMALIZED_PROBES = (
    'threadMain must reset pic_in[view] before qpfile parsing and readPicture reuse',
    'forbidden ABR thread pic_in reset regression: ',
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
                    'while (pic_in[0] && !b_ctrl_c)',
                    '{',
                    '    for (int view = 0; view < m_param->numViews - !!m_param->format; view++)',
                    '    {',
                    '        pic_in[view] = &pic_orig[view];',
                    '        if (!m_cliopt.parseQPFile(pic_orig[view]))',
                    '        {',
                    '            x265_log(nullptr, X265_LOG_ERROR, "can\'t parse qpfile for frame %d in %s\\n",',
                    '                pic_orig[view].poc, profileName);',
                    '        }',
                    '        else if (readPicture(pic_in[view], view)){',
                    '        }',
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
                    'while (pic_in[0] && !b_ctrl_c)',
                    '{',
                    '    else if (readPicture(pic_in[view], view)){',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread pic_in reset guardrail: pic_in[view] = &pic_orig[view];')

    print('ABR thread pic_in reset guard tests passed')


if __name__ == '__main__':
    main()
