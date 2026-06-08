#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_parameters_output_safety.py')

# Normalized checker probes used by the coverage scan for dynamic encoder-parameter output labels.
NORMALIZED_PROBES = (
    'param instance tracking must register on alloc and unregister on free before write-only copy helper',
    'forbidden  regression: ',
    'missing  guardrail: ',
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
                'source/encoder/api.cpp': '\n'.join((
                    'void x265_encoder_parameters(x265_encoder *enc, x265_param *out)',
                    '{',
                    '    if (enc && out)',
                    '    {',
                    '        Encoder *encoder = static_cast<Encoder*>(enc);',
                    '        if (isAllocatedParamInstance(out))',
                    '            x265_copy_params(out, encoder->m_param);',
                    '        else',
                    '            x265_copy_params_writeonly(out, encoder->m_param);',
                    '    }',
                    '}',
                )) + '\n',
                'source/common/param.cpp': '\n'.join((
                    'static bool registerParamInstance(x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'bool isAllocatedParamInstance(const x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'x265_param *x265_param_alloc()',
                    '{',
                    '    x265_param* param = (x265_param*)x265_malloc(sizeof(x265_param));',
                    '    if (!param)',
                    '        return nullptr;',
                    '    if (!registerParamInstance(param))',
                    '    {',
                    '        x265_free(param);',
                    '        return nullptr;',
                    '    }',
                    '    return param;',
                    '}',
                    'void x265_param_free(x265_param* p)',
                    '{',
                    '    unregisterParamInstance(p);',
                    '}',
                    'static void unregisterParamInstance(x265_param* param)',
                    '{',
                    '}',
                    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src)',
                    '{',
                    '    if (!prepareFreshParamCopyDestination(dst, src))',
                    '        return;',
                    '    x265_copy_params(dst, src);',
                    '}',
                )) + '\n',
                'source/common/param.h': '\n'.join((
                    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src);',
                    'bool isAllocatedParamInstance(const x265_param* param);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'void x265_encoder_parameters(x265_encoder *enc, x265_param *out)',
                    '{',
                    '    if (enc && out)',
                    '    {',
                    '        Encoder *encoder = static_cast<Encoder*>(enc);',
                    '        x265_copy_params(out, encoder->m_param);',
                    '    }',
                    '}',
                )) + '\n',
                'source/common/param.cpp': '\n'.join((
                    'static bool registerParamInstance(x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'static void unregisterParamInstance(x265_param* param)',
                    '{',
                    '}',
                    'bool isAllocatedParamInstance(const x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'x265_param *x265_param_alloc()',
                    '{',
                    '    x265_param* param = (x265_param*)x265_malloc(sizeof(x265_param));',
                    '    if (!param)',
                    '        return nullptr;',
                    '    if (!registerParamInstance(param))',
                    '    {',
                    '        x265_free(param);',
                    '        return nullptr;',
                    '    }',
                    '    return param;',
                    '}',
                    'void x265_param_free(x265_param* p)',
                    '{',
                    '    unregisterParamInstance(p);',
                    '}',
                    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src)',
                    '{',
                    '    x265_copy_params(dst, src);',
                    '}',
                )) + '\n',
                'source/common/param.h': 'void x265_copy_params_writeonly(x265_param* dst, x265_param* src);\nbool isAllocatedParamInstance(const x265_param* param);\n',
            },
        )
        expect_fail(run_checker(root), 'missing encoder parameters output safety guardrail: if (!prepareFreshParamCopyDestination(dst, src))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'void x265_encoder_parameters(x265_encoder *enc, x265_param *out)',
                    '{',
                    '    if (enc && out)',
                    '    {',
                    '        Encoder *encoder = static_cast<Encoder*>(enc);',
                    '        if (isAllocatedParamInstance(out))',
                    '            x265_copy_params_writeonly(out, encoder->m_param);',
                    '        else',
                    '            x265_copy_params(out, encoder->m_param);',
                    '    }',
                    '}',
                )) + '\n',
                'source/common/param.cpp': '\n'.join((
                    'static bool registerParamInstance(x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'static void unregisterParamInstance(x265_param* param)',
                    '{',
                    '}',
                    'bool isAllocatedParamInstance(const x265_param* param)',
                    '{',
                    '    return param != nullptr;',
                    '}',
                    'x265_param *x265_param_alloc()',
                    '{',
                    '    x265_param* param = (x265_param*)x265_malloc(sizeof(x265_param));',
                    '    if (!param)',
                    '        return nullptr;',
                    '    if (!registerParamInstance(param))',
                    '    {',
                    '        x265_free(param);',
                    '        return nullptr;',
                    '    }',
                    '    return param;',
                    '}',
                    'void x265_param_free(x265_param* p)',
                    '{',
                    '    unregisterParamInstance(p);',
                    '}',
                    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src)',
                    '{',
                    '    if (!prepareFreshParamCopyDestination(dst, src))',
                    '        return;',
                    '    x265_copy_params(dst, src);',
                    '}',
                )) + '\n',
                'source/common/param.h': '\n'.join((
                    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src);',
                    'bool isAllocatedParamInstance(const x265_param* param);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'encoder parameters output safety must keep allocated-instance reuse before write-only fallback')

    print('Encoder parameter output safety tests passed')


if __name__ == '__main__':
    main()
