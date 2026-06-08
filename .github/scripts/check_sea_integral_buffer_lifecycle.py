#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = {
    'header': Path('source/common/framedata.h'),
    'framedata': Path('source/common/framedata.cpp'),
    'dpb': Path('source/encoder/dpb.cpp'),
    'encoder': Path('source/encoder/encoder.cpp'),
}


def read_target(repo_root, key, failures):
    path = repo_root / TARGETS[key]
    if not path.is_file():
        failures.append((TARGETS[key].as_posix(), 0, 'missing file'))
        return ''
    return path.read_text(encoding='utf-8', errors='ignore')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    header = read_target(repo_root, 'header', failures)
    framedata = read_target(repo_root, 'framedata', failures)
    dpb = read_target(repo_root, 'dpb', failures)
    encoder = read_target(repo_root, 'encoder', failures)
    if failures:
        return failures

    header_required = 'void destroySEAIntegralBuffers();'
    if header_required not in header:
        failures.append((TARGETS['header'].as_posix(), 0, f'missing SEA integral buffer lifecycle guardrail: {header_required}'))

    framedata_required = (
        'void FrameData::destroySEAIntegralBuffers()',
        'if (m_meBuffer[i] != nullptr)',
        'X265_FREE(m_meBuffer[i]);',
        'm_meBuffer[i] = nullptr;',
        'm_meIntegral[i] = nullptr;',
        'destroySEAIntegralBuffers();',
    )
    for snippet in framedata_required:
        if snippet not in framedata:
            failures.append((TARGETS['framedata'].as_posix(), 0, f'missing SEA integral buffer lifecycle guardrail: {snippet}'))

    forbidden = 'X265_FREE(m_meIntegral[i]);'
    if forbidden in framedata:
        failures.append((TARGETS['framedata'].as_posix(), 0, f'forbidden SEA integral buffer lifecycle regression: {forbidden}'))

    helper_pos = framedata.find('void FrameData::destroySEAIntegralBuffers()')
    free_buffer_pos = framedata.find('X265_FREE(m_meBuffer[i]);', helper_pos if helper_pos != -1 else 0)
    null_buffer_pos = framedata.find('m_meBuffer[i] = nullptr;', free_buffer_pos if free_buffer_pos != -1 else 0)
    null_integral_pos = framedata.find('m_meIntegral[i] = nullptr;', null_buffer_pos if null_buffer_pos != -1 else 0)
    destroy_pos = framedata.find('void FrameData::destroy()')
    destroy_helper_pos = framedata.find('destroySEAIntegralBuffers();', destroy_pos if destroy_pos != -1 else 0)
    if -1 in (helper_pos, free_buffer_pos, null_buffer_pos, null_integral_pos, destroy_pos, destroy_helper_pos) or not (
        helper_pos < free_buffer_pos < null_buffer_pos < null_integral_pos < destroy_pos < destroy_helper_pos
    ):
        failures.append((TARGETS['framedata'].as_posix(), 0, 'FrameData must clear SEA integral ownership via destroySEAIntegralBuffers() before destroy() returns'))

    dpb_required = 'curFrame->m_encData->destroySEAIntegralBuffers();'
    if dpb_required not in dpb:
        failures.append((TARGETS['dpb'].as_posix(), 0, f'missing SEA integral buffer lifecycle guardrail: {dpb_required}'))

    encoder_required = (
        'frameEnc[layer]->m_encData->destroySEAIntegralBuffers();',
        'frameEnc[layer]->m_encData->m_meBuffer[i] = X265_MALLOC(',
        'if (frameEnc[layer]->m_encData->m_meBuffer[i])',
        'm_aborted = true;',
        'return -1;',
    )
    for snippet in encoder_required:
        if snippet not in encoder:
            failures.append((TARGETS['encoder'].as_posix(), 0, f'missing SEA integral buffer lifecycle guardrail: {snippet}'))

    alloc_loop_pos = encoder.find('for (int i = 0; i < INTEGRAL_PLANE_NUM; i++)')
    preclear_pos = encoder.rfind('frameEnc[layer]->m_encData->destroySEAIntegralBuffers();', 0, alloc_loop_pos if alloc_loop_pos != -1 else len(encoder))
    alloc_pos = encoder.find('frameEnc[layer]->m_encData->m_meBuffer[i] = X265_MALLOC(', alloc_loop_pos if alloc_loop_pos != -1 else 0)
    failure_clear_pos = encoder.find('frameEnc[layer]->m_encData->destroySEAIntegralBuffers();', alloc_pos if alloc_pos != -1 else 0)
    aborted_pos = encoder.find('m_aborted = true;', failure_clear_pos if failure_clear_pos != -1 else 0)
    return_pos = encoder.find('return -1;', aborted_pos if aborted_pos != -1 else 0)
    if -1 in (alloc_loop_pos, preclear_pos, alloc_pos, failure_clear_pos, aborted_pos, return_pos) or not (
        preclear_pos < alloc_loop_pos < alloc_pos < failure_clear_pos < aborted_pos < return_pos
    ):
        failures.append((TARGETS['encoder'].as_posix(), 0, 'SEA integral plane allocation must clear stale state before allocation and roll back all planes before aborting encode'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SEA integral buffer lifecycle')
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

    print('SEA integral buffer lifecycle validated')


if __name__ == '__main__':
    main()
