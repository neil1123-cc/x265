#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sao_create_rollback.py')

# Coverage probes used by the scan for SAO create rollback guardrails.
NORMALIZED_PROBES = (
    'forbidden SAO create rollback regression: ',
    'missing SAO create rollback guardrail: ',
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
                'source/encoder/sao.cpp': '\n'.join((
                    'bool SAO::create(x265_param* param, int initCommon)',
                    'CHECKED_MALLOC(m_tmpL1[i], pixel, m_param->maxCUSize + 1);',
                    'CHECKED_MALLOC(m_tmpU[i], pixel, m_numCuInWidth * m_param->maxCUSize + 2 + 32);',
                    'if (initCommon)',
                    'CHECKED_MALLOC(m_depthSaoRate, double, 2 * SAO_DEPTHRATE_SIZE);',
                    'CHECKED_MALLOC(m_clipTableBase,  pixel, maxY + 2 * rangeExt);',
                    'return true;',
                    'fail:',
                    '    destroy(initCommon);',
                    '    return false;',
                    'void SAO::createFromRootNode(SAO* root)',
                    '{',
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
                'source/encoder/sao.cpp': 'fail:\n    return false;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SAO create rollback regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/sao.cpp': '\n'.join((
                    'bool SAO::create(x265_param* param, int initCommon)',
                    'CHECKED_MALLOC(m_tmpL1[i], pixel, m_param->maxCUSize + 1);',
                    'CHECKED_MALLOC(m_tmpU[i], pixel, m_numCuInWidth * m_param->maxCUSize + 2 + 32);',
                    'if (initCommon)',
                    'CHECKED_MALLOC(m_depthSaoRate, double, 2 * SAO_DEPTHRATE_SIZE);',
                    'fail:',
                    '    destroy(initCommon);',
                    '    return false;',
                    'CHECKED_MALLOC(m_clipTableBase,  pixel, maxY + 2 * rangeExt);',
                    'return true;',
                    'void SAO::createFromRootNode(SAO* root)',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SAO::create must complete its staged allocation path before falling through to the shared destroy(initCommon) rollback')

    print('SAO create rollback tests passed')


if __name__ == '__main__':
    main()
