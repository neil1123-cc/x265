#!/usr/bin/env python3
import argparse
from pathlib import Path


FRAME_TARGET = Path('source/common/frame.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')
SIGNATURE = 'bool Frame::allocEncodeData(x265_param *param, const SPS& sps)'


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


def check_frame_alloc_encode_data(repo_root):
    path = repo_root / FRAME_TARGET
    if not path.is_file():
        return [(FRAME_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, SIGNATURE)
    if not func_text:
        return [(FRAME_TARGET.as_posix(), 0, 'missing Frame::allocEncodeData function')]

    failures = []
    required = (
        'FrameData* stagedEncData = new (std::nothrow) FrameData;',
        'PicYuv* stagedReconPic[NUM_RECON_VERSION] = { nullptr };',
        'stagedReconPic[i] = new (std::nothrow) PicYuv;',
        'if (!stagedEncData->create(*param, sps, m_fencPic->m_picCsp))',
        'if (!stagedReconPic[0]->create(param))',
        'if (sccEnabled && !stagedReconPic[1]->create(param))',
        'm_encData = stagedEncData;',
        'm_reconPic[i] = stagedReconPic[i];',
        'm_encData->m_reconPic[i] = stagedReconPic[i];',
        'stagedEncData->destroy();',
        'stagedReconPic[i]->destroy();',
    )
    for snippet in required:
        if snippet not in func_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'missing frame allocEncodeData guardrail: {snippet}'))

    forbidden = (
        'm_encData = new FrameData;',
        'm_reconPic[i] = new PicYuv;',
        'bool ok = m_encData->create(*param, sps, m_fencPic->m_picCsp) && m_reconPic[0]->create(param) && (!sccEnabled || m_reconPic[1]->create(param));',
    )
    for snippet in forbidden:
        if snippet in func_text:
            failures.append((FRAME_TARGET.as_posix(), 0, f'forbidden frame allocEncodeData regression: {snippet}'))

    create_pos = func_text.find('if (!stagedReconPic[0]->create(param))')
    commit_pos = func_text.find('m_encData = stagedEncData;')
    if -1 in (create_pos, commit_pos) or not (create_pos < commit_pos):
        failures.append((FRAME_TARGET.as_posix(), 0, 'Frame::allocEncodeData must fully initialize staged objects before publishing m_encData'))

    return failures


def check_encoder_caller(repo_root):
    path = repo_root / ENCODER_TARGET
    if not path.is_file():
        return [(ENCODER_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))',
        'm_aborted = true;',
        'x265_log(m_param, X265_LOG_ERROR, "memory allocation failure, aborting encode\\n");',
        'return -1;',
        'Slice* slice = frameEnc[layer]->m_encData->m_slice;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((ENCODER_TARGET.as_posix(), 0, f'missing Encoder::encode allocEncodeData guardrail: {snippet}'))

    call_pos = text.find('if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))')
    abort_pos = text.find('m_aborted = true;', call_pos if call_pos != -1 else 0)
    return_pos = text.find('return -1;', abort_pos if abort_pos != -1 else 0)
    slice_pos = text.find('Slice* slice = frameEnc[layer]->m_encData->m_slice;', call_pos if call_pos != -1 else 0)
    if -1 in (call_pos, abort_pos, return_pos, slice_pos) or not (call_pos < abort_pos < return_pos < slice_pos):
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::encode must abort on Frame::allocEncodeData failure before dereferencing m_encData'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    return check_frame_alloc_encode_data(repo_root) + check_encoder_caller(repo_root)


def main():
    parser = argparse.ArgumentParser(description='Check Frame::allocEncodeData staging and caller guards')
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

    print('Frame::allocEncodeData guardrails validated')


if __name__ == '__main__':
    main()
