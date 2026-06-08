#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mp4_handle_close_state.py')

# Coverage probes used by the scan for MP4 handle close-state guardrails.
NORMALIZED_PROBES = (
    'forbidden MP4 handle close-state regression: lsmash_close_file(&m_fileParam);',
    'missing MP4 handle close-state guardrail: if (lsmash_close_file(&m_fileParam) < 0)',
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
                'source/output/mp4.cpp': '\n'.join((
                    'void MP4Muxer::cleanupHandle()',
                    '{',
                    '    if (m_root)',
                    '    {',
                    '        if (m_fileOpen)',
                    '        {',
                    '            if (lsmash_close_file(&m_fileParam) < 0)',
                    '                m_fail = true;',
                    '            m_fileOpen = false;',
                    '        }',
                    '        lsmash_destroy_root(m_root);',
                    '        m_root = nullptr;',
                    '    }',
                    '}',
                    'void MP4Muxer::cleanupOutputFile()',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mp4.cpp': 'lsmash_close_file(&m_fileParam);\n'})
        expect_fail(run_checker(root), 'missing MP4 handle close-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mp4.cpp': '\n'.join((
                    'void MP4Muxer::cleanupHandle()',
                    '{',
                    '    if (m_fileOpen)',
                    '    {',
                    '        if (lsmash_close_file(&m_fileParam) < 0)',
                    '            m_fail = true;',
                    '        m_fileOpen = false;',
                    '        lsmash_close_file(&m_fileParam);',
                    '    }',
                    '}',
                    'void MP4Muxer::cleanupOutputFile()',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden MP4 handle close-state regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/mp4.cpp': '\n'.join((
                    'void MP4Muxer::cleanupHandle()',
                    '{',
                    '    if (m_root)',
                    '    {',
                    '        if (m_fileOpen)',
                    '        {',
                    '            m_fileOpen = false;',
                    '            if (lsmash_close_file(&m_fileParam) < 0)',
                    '                m_fail = true;',
                    '        }',
                    '        lsmash_destroy_root(m_root);',
                    '        m_root = nullptr;',
                    '    }',
                    '}',
                    'void MP4Muxer::cleanupOutputFile()',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'MP4 handle cleanup must resolve close failure before clearing file-open state and destroying the root')

    print('MP4 handle close-state guard tests passed')


if __name__ == '__main__':
    main()
