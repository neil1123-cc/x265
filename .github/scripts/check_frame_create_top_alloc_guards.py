#!/usr/bin/env python3
import argparse
from pathlib import Path


FRAME_TARGET = Path('source/common/frame.cpp')
TEMPORALFILTER_TARGET = Path('source/common/temporalfilter.cpp')
CTOR_SIGNATURE = 'Frame::Frame()'
FRAME_SIGNATURE = 'bool Frame::create(x265_param *param, float* quantOffsets)'
DESTROY_SIGNATURE = 'void Frame::destroy()'
TEMPORALFILTER_SIGNATURE = 'bool TemporalFilter::init(const x265_param* param)'


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_frame_create(repo_root):
    path = repo_root / FRAME_TARGET
    if not path.is_file():
        return [(FRAME_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    ctor_text = extract_braced_block(text, CTOR_SIGNATURE)
    create_text = extract_braced_block(text, FRAME_SIGNATURE)
    destroy_text = extract_braced_block(text, DESTROY_SIGNATURE)
    failures = []
    if not ctor_text:
        failures.append((FRAME_TARGET.as_posix(), 0, 'missing Frame::Frame constructor'))
        return failures
    if not create_text:
        failures.append((FRAME_TARGET.as_posix(), 0, 'missing Frame::create function'))
        return failures
    if not destroy_text:
        failures.append((FRAME_TARGET.as_posix(), 0, 'missing Frame::destroy function'))
        return failures

    required_ctor = (
        'm_fencPic = nullptr;',
        'm_fencPicSubsampled2 = nullptr;',
        'm_fencPicSubsampled4 = nullptr;',
        'm_mcstffencPic = nullptr;',
    )
    for snippet in required_ctor:
        if snippet not in ctor_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'missing frame constructor cleanup guardrail: {snippet}'))

    required_create = (
        'm_fencPic = new (std::nothrow) PicYuv;',
        'if (!m_fencPic)',
        'm_mcstf = new (std::nothrow) TemporalFilter;',
        'm_mcstffencPic = new (std::nothrow) PicYuv;',
        'if (!m_mcstf || !m_mcstffencPic)',
        'if (!m_mcstf->init(param))',
        'm_fencPicSubsampled2 = new (std::nothrow) PicYuv;',
        'm_fencPicSubsampled4 = new (std::nothrow) PicYuv;',
        'if (!m_fencPicSubsampled2 || !m_fencPicSubsampled4)',
    )
    for snippet in required_create:
        if snippet not in create_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'missing frame create top alloc guardrail: {snippet}'))

    forbidden_create = (
        'm_fencPic = new PicYuv;',
        'm_mcstf = new TemporalFilter;',
        'm_mcstffencPic = new PicYuv;',
        'm_fencPicSubsampled2 = new PicYuv;',
        'm_fencPicSubsampled4 = new PicYuv;',
        'm_mcstf->init(param);',
    )
    for snippet in forbidden_create:
        if snippet in create_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'forbidden frame create top alloc regression: {snippet}'))

    required_destroy = (
        'if (m_mcstf)',
        'delete m_mcstf->m_metld;',
        'm_mcstf->destroyRefPicInfo(&m_mcstfRefList[i]);',
        'delete m_mcstf;',
        'm_mcstf = nullptr;',
    )
    for snippet in required_destroy:
        if snippet not in destroy_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'missing frame destroy MCSTF cleanup guardrail: {snippet}'))

    mcstf_guard_pos = destroy_text.find('if (m_mcstf)')
    mcstf_delete_pos = destroy_text.find('delete m_mcstf;', mcstf_guard_pos if mcstf_guard_pos != -1 else 0)
    mcstf_null_pos = destroy_text.find('m_mcstf = nullptr;', mcstf_delete_pos if mcstf_delete_pos != -1 else 0)
    if -1 in (mcstf_guard_pos, mcstf_delete_pos, mcstf_null_pos) or not (mcstf_guard_pos < mcstf_delete_pos < mcstf_null_pos):
        failures.append((FRAME_TARGET.as_posix(), 0, 'Frame::destroy must tolerate partial MCSTF setup before deleting the temporal filter'))

    return failures


def check_temporalfilter_init(repo_root):
    path = repo_root / TEMPORALFILTER_TARGET
    if not path.is_file():
        return [(TEMPORALFILTER_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, TEMPORALFILTER_SIGNATURE)
    failures = []
    if not func_text:
        return [(TEMPORALFILTER_TARGET.as_posix(), 0, 'missing TemporalFilter::init function')]

    required = (
        'm_metld = new (std::nothrow) MotionEstimatorTLD;',
        'if (!hasMotionEstimatorTLDBuffers(m_metld))',
        'delete m_metld;',
        'm_metld = nullptr;',
        'return true;',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((TEMPORALFILTER_TARGET.as_posix(), 0, f'missing temporal filter init guardrail: {snippet}'))

    forbidden = (
        'm_metld = new MotionEstimatorTLD;',
        'return m_metld != nullptr;',
    )
    for snippet in forbidden:
        if snippet in func_text:
            failures.append((TEMPORALFILTER_TARGET.as_posix(), 0, f'forbidden temporal filter init regression: {snippet}'))

    alloc_pos = func_text.find('m_metld = new (std::nothrow) MotionEstimatorTLD;')
    guard_pos = func_text.find('if (!hasMotionEstimatorTLDBuffers(m_metld))', alloc_pos if alloc_pos != -1 else 0)
    delete_pos = func_text.find('delete m_metld;', guard_pos if guard_pos != -1 else 0)
    null_pos = func_text.find('m_metld = nullptr;', delete_pos if delete_pos != -1 else 0)
    return_false_pos = func_text.find('return false;', null_pos if null_pos != -1 else 0)
    return_true_pos = func_text.find('return true;', return_false_pos if return_false_pos != -1 else 0)
    if -1 in (alloc_pos, guard_pos, delete_pos, null_pos, return_false_pos, return_true_pos) or not (
        alloc_pos < guard_pos < delete_pos < null_pos < return_false_pos < return_true_pos
    ):
        failures.append((TEMPORALFILTER_TARGET.as_posix(), 0, 'TemporalFilter::init must validate MotionEstimatorTLD buffers and clear m_metld before returning success'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    return check_frame_create(repo_root) + check_temporalfilter_init(repo_root)


def main():
    parser = argparse.ArgumentParser(description='Check Frame::create top allocation guards')
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

    print('Frame::create top allocation guards validated')


if __name__ == '__main__':
    main()
