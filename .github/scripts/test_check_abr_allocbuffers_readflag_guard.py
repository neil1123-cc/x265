#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_allocbuffers_readflag_guard.py')


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
                    'bool AbrEncoder::allocBuffers()',
                    '{',
                    'if (primaryParam->numViews > 1)',
                    '{',
                    '    if (pass == 0)',
                    '    {',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    'else',
                    '{',
                    '    for (uint8_t pass = 0; pass < m_numEncodes; pass++)',
                    '    {',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    '#if ENABLE_MULTIVIEW',
                    'fail:',
                    '    return false;',
                    '#endif',
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
                    'm_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    'm_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr allocBuffers readFlag guardrail: if (!m_readFlag[pass])')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'bool AbrEncoder::allocBuffers()',
                    '{',
                    'if (primaryParam->numViews > 1)',
                    '{',
                    '    if (pass == 0)',
                    '    {',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    'else',
                    '{',
                    '    for (uint8_t pass = 0; pass < m_numEncodes; pass++)',
                    '    {',
                    '        something_else();',
                    '    }',
                    '}',
                    '#if ENABLE_MULTIVIEW',
                    'fail:',
                    '    return false;',
                    '#endif',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'AbrEncoder::allocBuffers must guard m_readFlag[pass] allocation in both queue setup branches')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (primaryParam->numViews > 1)',
                    '{',
                    '    if (pass == 0)',
                    '    {',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    '}',
                    'bool AbrEncoder::allocBuffers()',
                    '{',
                    'if (primaryParam->numViews > 1)',
                    '{',
                    '    something_else();',
                    '}',
                    'else',
                    '{',
                    '    for (uint8_t pass = 0; pass < m_numEncodes; pass++)',
                    '    {',
                    '        m_readFlag[pass] = X265_MALLOC(int, m_queueSize);',
                    '        if (!m_readFlag[pass])',
                    '            goto fail;',
                    '    }',
                    '}',
                    '#if ENABLE_MULTIVIEW',
                    'fail:',
                    '    return false;',
                    '#endif',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'AbrEncoder::allocBuffers must guard m_readFlag[pass] allocation in both queue setup branches')

    print('AbrEncoder allocBuffers readFlag guard tests passed')


if __name__ == '__main__':
    main()
