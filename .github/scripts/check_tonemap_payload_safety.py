#!/usr/bin/env python3
import argparse
from pathlib import Path


ENCODER_TARGET = Path('source/encoder/encoder.cpp')
FRAMEENCODER_TARGET = Path('source/encoder/frameencoder.cpp')

ENCODER_REQUIRED_SNIPPETS = (
    'x265_sei_payload toneMap = {};',
    'toneMap.payloadType = USER_DATA_REGISTERED_ITU_T_T35;',
    'const int toneMapMetadataBytes = 509;',
    'if (currentPOC >= 0 && currentPOC < m_numCimInfo && m_cim && m_cim[currentPOC])',
    'while (payloadPrefixBytes < toneMapMetadataBytes && m_cim[currentPOC][payloadPrefixBytes] == 0xFF)',
    'if (payloadSize > INT_MAX - 0xFF)',
    'if (payloadPrefixBytes >= toneMapMetadataBytes || payloadSize < 0 ||',
    'x265_log(m_param, X265_LOG_ERROR, "Invalid HDR10+ tone-map payload prefix for frame %d\\n", currentPOC);',
    'if (payloadSize > toneMapMetadataBytes - payloadPrefixBytes - 1)',
    'x265_log(m_param, X265_LOG_ERROR, "HDR10+ tone-map payload exceeds frame metadata buffer for frame %d\\n", currentPOC);',
    'uint8_t* stagedToneMapPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payloadSize);',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate HDR10+ tone-map payload buffer\\n");',
    'toneMap.payload = stagedToneMapPayload;',
    'toneMap.payloadSize = payloadSize;',
    'if (i < pic_in->userSEI.numPayloads)',
    'else if (userPayload && i == pic_in->userSEI.numPayloads)',
    'else',
    'input = toneMap;',
)

ENCODER_FORBIDDEN_SNIPPETS = (
    'while (m_cim[currentPOC][i] == 0xFF)',
    'toneMap.payload = (uint8_t*)x265_malloc(sizeof(uint8_t) * toneMap.payloadSize);',
    'else if (m_enableNal)',
)

FRAMEENCODER_REQUIRED_SNIPPETS = (
    'uint8_t* stagedPayload = nullptr;',
    'stagedPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payload->payloadSize);',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate tone-map payload history buffer\\n");',
    'std::memcpy(stagedPayload, payload->payload, payload->payloadSize);',
    'x265_free(m_top->m_prevTonemapPayload.payload);',
    'm_top->m_prevTonemapPayload.payload = stagedPayload;',
)

FRAMEENCODER_FORBIDDEN_SNIPPETS = (
    'if (m_top->m_prevTonemapPayload.payload != nullptr)\n            x265_free(m_top->m_prevTonemapPayload.payload);\n        m_top->m_prevTonemapPayload.payload = (uint8_t*)x265_malloc(sizeof(uint8_t)* payload->payloadSize);',
    'std::memcpy(m_top->m_prevTonemapPayload.payload, payload->payload, payload->payloadSize);',
)


def require_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet not in text:
            failures.append((target.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def forbid_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet in text:
            failures.append((target.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    encoder_path = repo_root / ENCODER_TARGET
    if not encoder_path.is_file():
        failures.append((ENCODER_TARGET.as_posix(), 0, 'missing file'))
    else:
        encoder_text = encoder_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(encoder_text, ENCODER_TARGET, ENCODER_REQUIRED_SNIPPETS, 'tone-map payload safety'))
        failures.extend(forbid_snippets(encoder_text, ENCODER_TARGET, ENCODER_FORBIDDEN_SNIPPETS, 'tone-map payload safety'))

        func_pos = encoder_text.find('void Encoder::copyUserSEIMessages(Frame *frame, const x265_picture* pic_in)')
        hdr_guard_pos = encoder_text.find('if (currentPOC >= 0 && currentPOC < m_numCimInfo && m_cim && m_cim[currentPOC])', func_pos if func_pos != -1 else 0)
        prefix_loop_pos = encoder_text.find('while (payloadPrefixBytes < toneMapMetadataBytes && m_cim[currentPOC][payloadPrefixBytes] == 0xFF)', hdr_guard_pos if hdr_guard_pos != -1 else 0)
        prefix_check_pos = encoder_text.find('if (payloadPrefixBytes >= toneMapMetadataBytes || payloadSize < 0 ||', prefix_loop_pos if prefix_loop_pos != -1 else 0)
        size_check_pos = encoder_text.find('if (payloadSize > toneMapMetadataBytes - payloadPrefixBytes - 1)', prefix_check_pos if prefix_check_pos != -1 else 0)
        alloc_pos = encoder_text.find('uint8_t* stagedToneMapPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payloadSize);', size_check_pos if size_check_pos != -1 else 0)
        tone_assign_pos = encoder_text.find('toneMap.payload = stagedToneMapPayload;', alloc_pos if alloc_pos != -1 else 0)
        pick_pic_pos = encoder_text.find('if (i < pic_in->userSEI.numPayloads)', tone_assign_pos if tone_assign_pos != -1 else 0)
        pick_user_pos = encoder_text.find('else if (userPayload && i == pic_in->userSEI.numPayloads)', pick_pic_pos if pick_pic_pos != -1 else 0)
        pick_tone_pos = encoder_text.find('input = toneMap;', pick_user_pos if pick_user_pos != -1 else 0)
        if -1 in (func_pos, hdr_guard_pos, prefix_loop_pos, prefix_check_pos, size_check_pos, alloc_pos, tone_assign_pos, pick_pic_pos, pick_user_pos, pick_tone_pos) or not (
            func_pos < hdr_guard_pos < prefix_loop_pos < prefix_check_pos < size_check_pos < alloc_pos < tone_assign_pos < pick_pic_pos < pick_user_pos < pick_tone_pos
        ):
            failures.append((ENCODER_TARGET.as_posix(), 0, 'copyUserSEIMessages must bound-check HDR10+ metadata, stage tone-map payloads safely, and append nalu/tone-map payloads after original user SEI payloads'))

    frameencoder_path = repo_root / FRAMEENCODER_TARGET
    if not frameencoder_path.is_file():
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'missing file'))
    else:
        frameencoder_text = frameencoder_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(frameencoder_text, FRAMEENCODER_TARGET, FRAMEENCODER_REQUIRED_SNIPPETS, 'tone-map history replace safety'))
        failures.extend(forbid_snippets(frameencoder_text, FRAMEENCODER_TARGET, FRAMEENCODER_FORBIDDEN_SNIPPETS, 'tone-map history replace safety'))

        func_pos = frameencoder_text.find('bool FrameEncoder::writeToneMapInfo(x265_sei_payload *payload)')
        change_pos = frameencoder_text.find('if (payloadChange)', func_pos if func_pos != -1 else 0)
        staged_decl_pos = frameencoder_text.find('uint8_t* stagedPayload = nullptr;', change_pos if change_pos != -1 else 0)
        staged_alloc_pos = frameencoder_text.find('stagedPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payload->payloadSize);', staged_decl_pos if staged_decl_pos != -1 else 0)
        staged_copy_pos = frameencoder_text.find('std::memcpy(stagedPayload, payload->payload, payload->payloadSize);', staged_alloc_pos if staged_alloc_pos != -1 else 0)
        free_pos = frameencoder_text.find('x265_free(m_top->m_prevTonemapPayload.payload);', staged_copy_pos if staged_copy_pos != -1 else 0)
        assign_pos = frameencoder_text.find('m_top->m_prevTonemapPayload.payload = stagedPayload;', free_pos if free_pos != -1 else 0)
        if -1 in (func_pos, change_pos, staged_decl_pos, staged_alloc_pos, staged_copy_pos, free_pos, assign_pos) or not (
            func_pos < change_pos < staged_decl_pos < staged_alloc_pos < staged_copy_pos < free_pos < assign_pos
        ):
            failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'writeToneMapInfo must allocate replacement payload storage before dropping the old tone-map history payload'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check tone-map payload safety guardrails')
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

    print('Tone-map payload safety validated')


if __name__ == '__main__':
    main()
