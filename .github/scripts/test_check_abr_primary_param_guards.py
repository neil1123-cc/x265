#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_primary_param_guards.py')


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
                    'void AbrEncoder::encode()',
                    '{',
                    'PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;',
                    'x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;',
                    'if (!primaryParam)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing primary ABR parameters\\n");',
                    '}',
                    'm_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;',
                    '}',
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (!m_param)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing encoder parameters for encoder %u\\n", m_id);',
                    '}',
                    'PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];',
                    'if (!srcPass || !srcPass->m_param)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing scaler source parameters for encoder %u\\n", m_id);',
                    '}',
                    'int dstW = srcPass->m_param->sourceWidth;',
                    'int dstH = srcPass->m_param->sourceHeight;',
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
                'source/abrEncApp.cpp': 'm_numInputViews = (m_passEnc[0]->m_param->numViews > 1) ? m_passEnc[0]->m_param->numViews - !!m_passEnc[0]->m_param->format : 0;\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR primary/scaler param guardrail: PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void AbrEncoder::encode()',
                    '{',
                    '    something_else();',
                    '}',
                    'bool AbrEncoder::allocBuffers()',
                    '{',
                    'PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;',
                    'x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;',
                    'if (!primaryParam)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing primary ABR parameters\\n");',
                    '}',
                    'm_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;',
                    '}',
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (!m_param)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing encoder parameters for encoder %u\\n", m_id);',
                    '}',
                    'PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];',
                    'if (!srcPass || !srcPass->m_param)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing scaler source parameters for encoder %u\\n", m_id);',
                    '}',
                    'int dstW = srcPass->m_param->sourceWidth;',
                    'int dstH = srcPass->m_param->sourceHeight;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'AbrEncoder::encode must guard primaryParam before deriving m_numInputViews')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void AbrEncoder::encode()',
                    '{',
                    'PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;',
                    'x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;',
                    'if (!primaryParam)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing primary ABR parameters\\n");',
                    '}',
                    'm_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;',
                    '}',
                    'PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];',
                    'if (!srcPass || !srcPass->m_param)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing scaler source parameters for encoder %u\\n", m_id);',
                    '}',
                    'int dstW = srcPass->m_param->sourceWidth;',
                    'int dstH = srcPass->m_param->sourceHeight;',
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (!m_param)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Missing encoder parameters for encoder %u\\n", m_id);',
                    '}',
                    '    something_else();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::init must guard scaler source parameters before reading destination dimensions')

    print('ABR primary/scaler parameter guard tests passed')


if __name__ == '__main__':
    main()
