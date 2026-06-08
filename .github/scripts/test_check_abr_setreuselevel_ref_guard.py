#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_setreuselevel_ref_guard.py')


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
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (m_parent->m_numEncodes > 1)',
                    '    setReuseLevel();',
                    'if (m_ret)',
                    '{',
                    '    if (!result)',
                    '        result = m_ret;',
                    '    return -1;',
                    '}',
                    '}',
                    'void PassEncoder::setReuseLevel()',
                    '{',
                    'if (m_cliopt.loadLevel)',
                    '{',
                    '    PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];',
                    '    if (!refPass || !refPass->m_param)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing reference analysis parameters for encoder %u\\n", m_id);',
                    '        m_ret = 4;',
                    '    }',
                    '    else',
                    '    {',
                    '        x265_param *refParam = refPass->m_param;',
                    '        int srcH = refParam->sourceHeight - refParam->confWinBottomOffset;',
                    '        int srcW = refParam->sourceWidth - refParam->confWinRightOffset;',
                    '        if (m_param->sourceHeight == srcH &&',
                    '            m_param->sourceWidth == srcW)',
                    '        {',
                    '        }',
                    '        else if (srcH > 0 && srcW > 0)',
                    '        {',
                    '            double scaleFactorH = double(m_param->sourceHeight) / srcH;',
                    '            double scaleFactorW = double(m_param->sourceWidth) / srcW;',
                    '        }',
                    '    }',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'x265_param *refParam = m_parent->m_passEnc[m_cliopt.refId]->m_param;\n'})
        expect_fail(run_checker(root), 'missing ABR setReuseLevel ref guardrail: PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (m_parent->m_numEncodes > 1)',
                    '    setReuseLevel();',
                    '}',
                    'void PassEncoder::setReuseLevel()',
                    '{',
                    'if (m_cliopt.loadLevel)',
                    '{',
                    '    PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];',
                    '    if (!refPass || !refPass->m_param)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing reference analysis parameters for encoder %u\\n", m_id);',
                    '        m_ret = 4;',
                    '    }',
                    '    else',
                    '    {',
                    '        x265_param *refParam = refPass->m_param;',
                    '        int srcH = refParam->sourceHeight - refParam->confWinBottomOffset;',
                    '        int srcW = refParam->sourceWidth - refParam->confWinRightOffset;',
                    '        else if (srcH > 0 && srcW > 0)',
                    '        {',
                    '            double scaleFactorH = double(m_param->sourceHeight) / srcH;',
                    '            double scaleFactorW = double(m_param->sourceWidth) / srcW;',
                    '        }',
                    '    }',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::init must stop immediately when setReuseLevel reports failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (m_cliopt.loadLevel)',
                    '{',
                    '    PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];',
                    '    if (!refPass || !refPass->m_param)',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Missing reference analysis parameters for encoder %u\\n", m_id);',
                    '        m_ret = 4;',
                    '    }',
                    '    else',
                    '    {',
                    '        x265_param *refParam = refPass->m_param;',
                    '        int srcH = refParam->sourceHeight - refParam->confWinBottomOffset;',
                    '        int srcW = refParam->sourceWidth - refParam->confWinRightOffset;',
                    '        else if (srcH > 0 && srcW > 0)',
                    '        {',
                    '            double scaleFactorH = double(m_param->sourceHeight) / srcH;',
                    '            double scaleFactorW = double(m_param->sourceWidth) / srcW;',
                    '        }',
                    '    }',
                    '}',
                    '}',
                    'void PassEncoder::setReuseLevel()',
                    '{',
                    '    something_else();',
                    '}',
                    'int PassEncoder::init(int &result)',
                    '{',
                    'if (m_parent->m_numEncodes > 1)',
                    '    setReuseLevel();',
                    'if (m_ret)',
                    '{',
                    '    if (!result)',
                    '        result = m_ret;',
                    '    return -1;',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::setReuseLevel must guard refPass/refParam and positive scaled dimensions before reuse math')

    print('ABR setReuseLevel reference guard tests passed')


if __name__ == '__main__':
    main()
