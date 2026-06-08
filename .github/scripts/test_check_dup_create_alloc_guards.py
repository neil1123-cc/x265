#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_dup_create_alloc_guards.py')

# Coverage probes used by the scan for duplication create guardrails.
NORMALIZED_PROBES = (
    'duplication create must check each allocation before dereferencing the next object',
    'forbidden duplication create alloc regression: ',
    'missing duplication create alloc guardrail: ',
    """m_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));
            m_dupBuffer[i]->dupPic = nullptr;""",
    """m_dupPicOne[0] = X265_MALLOC(pixel, size);
            m_dupPicTwo[0] = X265_MALLOC(pixel, size);
            if (p->internalCsp != X265_CSP_I400)""",
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));',
                    'if (!m_dupBuffer[i])',
                    '    return;',
                    'm_dupBuffer[i]->dupPic = x265_picture_alloc();',
                    'if (!m_dupBuffer[i]->dupPic)',
                    '    return;',
                    'm_dupBuffer[i]->dupPlane = X265_MALLOC(char, framesize);',
                    'if (!m_dupBuffer[i]->dupPlane)',
                    '    return;',
                    'if (!m_dupPicOne[0] || !m_dupPicTwo[0])',
                    '    return;',
                    'if (!m_dupPicOne[k] || !m_dupPicTwo[k])',
                    '    return;',
                    'm_aborted = true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'm_dupBuffer[i] = (AdaptiveFrameDuplication*)x265_malloc(sizeof(AdaptiveFrameDuplication));',
                    'm_dupBuffer[i]->dupPic = nullptr;',
                    'm_dupBuffer[i]->dupPic = x265_picture_alloc();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing duplication create alloc guardrail')

    print('Duplication create allocation guard tests passed')


if __name__ == '__main__':
    main()
