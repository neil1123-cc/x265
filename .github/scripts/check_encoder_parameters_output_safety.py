#!/usr/bin/env python3
import argparse
from pathlib import Path


API_TARGET = Path('source/encoder/api.cpp')
PARAM_TARGET = Path('source/common/param.cpp')
HEADER_TARGET = Path('source/common/param.h')

API_REQUIRED_SNIPPETS = (
    'void x265_encoder_parameters(x265_encoder *enc, x265_param *out)',
    'if (isAllocatedParamInstance(out))',
    'x265_copy_params(out, encoder->m_param);',
    'x265_copy_params_writeonly(out, encoder->m_param);',
)
PARAM_REQUIRED_SNIPPETS = (
    'bool isAllocatedParamInstance(const x265_param* param)',
    'static bool registerParamInstance(x265_param* param)',
    'static void unregisterParamInstance(x265_param* param)',
    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src)',
    'if (!prepareFreshParamCopyDestination(dst, src))',
    'x265_copy_params(dst, src);',
    'if (!registerParamInstance(param))',
    'unregisterParamInstance(p);',
)
HEADER_REQUIRED_SNIPPETS = (
    'void x265_copy_params_writeonly(x265_param* dst, x265_param* src);',
    'bool isAllocatedParamInstance(const x265_param* param);',
)
API_FORBIDDEN_SNIPPETS = (
    'x265_copy_params(out, encoder->m_param);\n    }\n}',
)
WRAPPER_GUARD_MESSAGE = 'encoder parameters output safety must keep C API namespace wrappers inside EXPORT_C_API guard'


def check_text(path, text, required, forbidden, label):
    failures = []
    for snippet in forbidden:
        if snippet in text:
            failures.append((path.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
            return failures
    for snippet in required:
        if snippet not in text:
            failures.append((path.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def check_exported_api_namespace_wrappers(param_text):
    failures = []
    instance_marker = 'return ::isAllocatedParamInstance(param);'
    finalize_marker = '::finalizeZoneParamCopy(zoneParam, src);'
    instance_pos = param_text.find(instance_marker)
    finalize_pos = param_text.find(finalize_marker, instance_pos if instance_pos != -1 else 0)
    if instance_pos == -1 and finalize_pos == -1:
        return failures

    namespace_pos = param_text.rfind('namespace X265_NS {', 0, instance_pos)
    guard_pos = param_text.rfind('#if EXPORT_C_API', 0, namespace_pos)
    endif_pos = param_text.find('#endif', finalize_pos)
    internal_namespace_pos = param_text.find('namespace X265_NS {\n// internal encoder functions', endif_pos)
    if -1 in (instance_pos, finalize_pos, namespace_pos, guard_pos, endif_pos, internal_namespace_pos):
        failures.append((PARAM_TARGET.as_posix(), 0, WRAPPER_GUARD_MESSAGE))
        return failures

    if param_text[guard_pos + len('#if EXPORT_C_API'):namespace_pos].strip():
        failures.append((PARAM_TARGET.as_posix(), 0, WRAPPER_GUARD_MESSAGE))
    elif not (guard_pos < namespace_pos < instance_pos < finalize_pos < endif_pos < internal_namespace_pos):
        failures.append((PARAM_TARGET.as_posix(), 0, WRAPPER_GUARD_MESSAGE))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    api_path = repo_root / API_TARGET
    param_path = repo_root / PARAM_TARGET
    header_path = repo_root / HEADER_TARGET
    failures = []

    for path in (api_path, param_path, header_path):
        if not path.is_file():
            return [(path.as_posix(), 0, 'missing file')]

    api_text = api_path.read_text(encoding='utf-8', errors='ignore')
    param_text = param_path.read_text(encoding='utf-8', errors='ignore')
    header_text = header_path.read_text(encoding='utf-8', errors='ignore')

    failures.extend(check_text(API_TARGET, api_text, API_REQUIRED_SNIPPETS, API_FORBIDDEN_SNIPPETS, 'encoder parameters output safety'))
    failures.extend(check_text(PARAM_TARGET, param_text, PARAM_REQUIRED_SNIPPETS, (), 'encoder parameters output safety'))
    failures.extend(check_text(HEADER_TARGET, header_text, HEADER_REQUIRED_SNIPPETS, (), 'encoder parameters output safety'))
    failures.extend(check_exported_api_namespace_wrappers(param_text))

    branch_pos = api_text.find('if (isAllocatedParamInstance(out))')
    copy_pos = api_text.find('x265_copy_params(out, encoder->m_param);', branch_pos if branch_pos != -1 else 0)
    writeonly_pos = api_text.find('x265_copy_params_writeonly(out, encoder->m_param);', copy_pos if copy_pos != -1 else 0)
    if -1 in (branch_pos, copy_pos, writeonly_pos) or not (branch_pos < copy_pos < writeonly_pos):
        failures.append((API_TARGET.as_posix(), 0, 'encoder parameters output safety must keep allocated-instance reuse before write-only fallback'))

    alloc_pos = param_text.find('if (!registerParamInstance(param))')
    free_pos = param_text.find('unregisterParamInstance(p);')
    writeonly_decl_pos = param_text.find('void x265_copy_params_writeonly(x265_param* dst, x265_param* src)')
    if -1 in (alloc_pos, free_pos, writeonly_decl_pos):
        return failures
    if not (alloc_pos < free_pos < writeonly_decl_pos):
        failures.append((PARAM_TARGET.as_posix(), 0, 'param instance tracking must register on alloc and unregister on free before write-only copy helper'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder parameter output safety guardrails')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Encoder parameter output safety validated')


if __name__ == '__main__':
    main()
