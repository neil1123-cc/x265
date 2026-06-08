#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_scaler_videodesc_alloc_guard.py')

# Coverage probes used by the scan for ABR VideoDesc allocation guardrails.
NORMALIZED_PROBES = (
    'ABR scaler VideoDesc allocations must use nothrow and feed the existing null guard',
    'missing ABR scaler VideoDesc alloc guardrail: ',
    'forbidden ABR scaler VideoDesc allocation pattern: ',
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
                    'dst = new (std::nothrow) VideoDesc(m_param->sourceWidth, m_param->sourceHeight, m_param->internalCsp, m_param->internalBitDepth);',
                    'src = new (std::nothrow) VideoDesc(dstW, dstH, m_param->internalCsp, m_param->internalBitDepth);',
                    'if (!src || !dst)',
                    '{',
                    '    delete src;',
                    '    delete dst;',
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
                    'dst = new VideoDesc(m_param->sourceWidth, m_param->sourceHeight, m_param->internalCsp, m_param->internalBitDepth);',
                    'src = new VideoDesc(dstW, dstH, m_param->internalCsp, m_param->internalBitDepth);',
                    'if (!src || !dst)',
                    '{',
                    '    delete src;',
                    '    delete dst;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR scaler VideoDesc alloc guardrail')

    print('ABR scaler VideoDesc allocation guard tests passed')


if __name__ == '__main__':
    main()
