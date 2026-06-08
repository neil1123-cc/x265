#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_allocbuffers_queue_guards.py')


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
                    '    m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '    if (!m_inputPicBuffer[pass])',
                    '        goto fail;',
                    '    for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '    {',
                    '        m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '        if (!m_inputPicBuffer[pass][idx])',
                    '        {',
                    '            while (idx--)',
                    '                x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '            X265_FREE(m_inputPicBuffer[pass]);',
                    '            m_inputPicBuffer[pass] = nullptr;',
                    '            goto fail;',
                    '        }',
                    '    }',
                    '}',
                    'else',
                    '{',
                    '    for (uint8_t pass = 0; pass < m_numEncodes; pass++)',
                    '    {',
                    '        m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '        if (!m_inputPicBuffer[pass])',
                    '            goto fail;',
                    '        for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '        {',
                    '            m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '            if (!m_inputPicBuffer[pass][idx])',
                    '            {',
                    '                while (idx--)',
                    '                    x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '                X265_FREE(m_inputPicBuffer[pass]);',
                    '                m_inputPicBuffer[pass] = nullptr;',
                    '                goto fail;',
                    '            }',
                    '        }',
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
                    'm_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    'for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '{',
                    '    m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '}',
                    'm_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    'for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '{',
                    '    m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr allocBuffers queue guardrail: if (!m_inputPicBuffer[pass])')

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
                    '    m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '    if (!m_inputPicBuffer[pass])',
                    '        goto fail;',
                    '    for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '    {',
                    '        m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '        if (!m_inputPicBuffer[pass][idx])',
                    '        {',
                    '            while (idx--)',
                    '                x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '            X265_FREE(m_inputPicBuffer[pass]);',
                    '            m_inputPicBuffer[pass] = nullptr;',
                    '            goto fail;',
                    '        }',
                    '    }',
                    '    m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '    if (!m_inputPicBuffer[pass])',
                    '        goto fail;',
                    '    for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '    {',
                    '        m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '        if (!m_inputPicBuffer[pass][idx])',
                    '        {',
                    '            while (idx--)',
                    '                x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '            X265_FREE(m_inputPicBuffer[pass]);',
                    '            m_inputPicBuffer[pass] = nullptr;',
                    '            goto fail;',
                    '        }',
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
        expect_fail(run_checker(root), 'AbrEncoder::allocBuffers must guard queue picture buffers and picture allocation in both queue setup branches')

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
                    '    m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '    if (!m_inputPicBuffer[pass])',
                    '        goto fail;',
                    '    for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '    {',
                    '        m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '        if (!m_inputPicBuffer[pass][idx])',
                    '        {',
                    '            while (idx--)',
                    '                x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '            X265_FREE(m_inputPicBuffer[pass]);',
                    '            m_inputPicBuffer[pass] = nullptr;',
                    '            goto fail;',
                    '        }',
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
                    '        m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);',
                    '        if (!m_inputPicBuffer[pass])',
                    '            goto fail;',
                    '        for (uint32_t idx = 0; idx < m_queueSize; idx++)',
                    '        {',
                    '            m_inputPicBuffer[pass][idx] = x265_picture_alloc();',
                    '            if (!m_inputPicBuffer[pass][idx])',
                    '            {',
                    '                while (idx--)',
                    '                    x265_picture_free(m_inputPicBuffer[pass][idx]);',
                    '                X265_FREE(m_inputPicBuffer[pass]);',
                    '                m_inputPicBuffer[pass] = nullptr;',
                    '                goto fail;',
                    '            }',
                    '        }',
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
        expect_fail(run_checker(root), 'AbrEncoder::allocBuffers must guard queue picture buffers and picture allocation in both queue setup branches')

    print('AbrEncoder allocBuffers queue guard tests passed')


if __name__ == '__main__':
    main()
