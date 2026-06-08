#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'if (encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
    'uint8_t* newPayload = X265_MALLOC(uint8_t, payloadSize);',
    'if (!newPayload)',
    'x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate Dolby Vision RPU payload buffer\\n");',
    'numEncoded = -1;',
    'goto fail;',
    'X265_FREE(inputData->dolbyVisionRpu.payload);',
    'inputData->dolbyVisionRpu.payload = newPayload;',
    'encoder->m_svtAppData->dolbyVisionRpuCapacity = payloadSize;',
    'memcpy(inputData->dolbyVisionRpu.payload, pic_in->rpu.payload, payloadSize);',
    'if (inputData->dolbyVisionRpu.payload)',
    'inputData->dolbyVisionRpu.payload = nullptr;',
    'encoder->m_svtAppData->dolbyVisionRpuCapacity = 0;',
    'inputData->dolbyVisionRpu.payloadSize = 0;',
)
FORBIDDEN_SNIPPETS = (
    'if (inputData->dolbyVisionRpu.payload && encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
    'inputData->dolbyVisionRpu.payload = X265_MALLOC(uint8_t, payloadSize);',
)
REGION_START = 'if (pic_in->rpu.payloadSize)'
REGION_END = 'return_error = EbH265EncSendPicture(encoder->m_svtAppData->svtEncoderHandle, inputPtr);'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT RPU payload replace regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing SVT RPU payload replace guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
                'uint8_t* newPayload = X265_MALLOC(uint8_t, payloadSize);',
                'if (!newPayload)',
                'x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate Dolby Vision RPU payload buffer\\n");',
                'numEncoded = -1;',
                'goto fail;',
                'X265_FREE(inputData->dolbyVisionRpu.payload);',
                'inputData->dolbyVisionRpu.payload = newPayload;',
                'encoder->m_svtAppData->dolbyVisionRpuCapacity = payloadSize;',
                'memcpy(inputData->dolbyVisionRpu.payload, pic_in->rpu.payload, payloadSize);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT RPU payload replacement must allocate the new payload before releasing and replacing the prior payload buffer'))
        if not has_in_order(
            region,
            (
                'if (inputData->dolbyVisionRpu.payload)',
                'X265_FREE(inputData->dolbyVisionRpu.payload);',
                'inputData->dolbyVisionRpu.payload = nullptr;',
                'encoder->m_svtAppData->dolbyVisionRpuCapacity = 0;',
                'inputData->dolbyVisionRpu.payloadSize = 0;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT RPU payload clear path must drop the payload pointer before resetting capacity and payload size'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT RPU payload replace safety guardrails')
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

    print('SVT RPU payload replace safety validated')


if __name__ == '__main__':
    main()
