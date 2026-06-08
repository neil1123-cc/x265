#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'SvtAppContext* stagedAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
    'if (!stagedAppData)',
    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData), sizeof(SvtAppContext), uint8_t(0));',
    'stagedAppData->svtHevcParams = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
    'if (!stagedAppData->svtHevcParams)',
    'X265_FREE(stagedAppData);',
    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData->svtHevcParams), sizeof(EB_H265_ENC_CONFIGURATION), uint8_t(0));',
    'stagedAppData->dolbyVisionRpuCapacity = 0;',
    'stagedAppData->byteCount = 0;',
    'stagedAppData->outFrameCount = 0;',
    'encoder->m_svtAppData = stagedAppData;',
    'return true;',
    'EB_BUFFERHEADERTYPE* stagedInputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
    'if (!stagedInputPictureBuffer)',
    'std::fill_n(reinterpret_cast<uint8_t*>(stagedInputPictureBuffer), sizeof(EB_BUFFERHEADERTYPE), uint8_t(0));',
    'EB_BUFFERHEADERTYPE *inputPtr = stagedInputPictureBuffer;',
    'inputPtr->pBuffer = (unsigned char*)x265_malloc(sizeof(EB_H265_ENC_INPUT));',
    'if (!inputPtr->pBuffer)',
    'X265_FREE(stagedInputPictureBuffer);',
    'inputData->dolbyVisionRpu.payloadSize = 0;',
    'inputPtr->nSize = sizeof(EB_BUFFERHEADERTYPE);',
    'encoder->m_svtAppData->inputPictureBuffer = stagedInputPictureBuffer;',
)
FORBIDDEN_SNIPPETS = (
    'encoder->m_svtAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
    'encoder->m_svtAppData->inputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
    'svt_release_app_context(encoder);\n        return false;',
)
APP_REGION_START = 'bool svt_initialise_app_context(x265_encoder *enc)'
APP_REGION_END = 'bool svt_initialise_input_buffer(x265_encoder *enc)'
INPUT_REGION_START = 'bool svt_initialise_input_buffer(x265_encoder *enc)'
INPUT_REGION_END = '#endif // ifdef SVT_HEVC'


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
    app_region = get_region(text, APP_REGION_START, APP_REGION_END)
    input_region = get_region(text, INPUT_REGION_START, INPUT_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT app-context staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT app-context staging guardrail: {snippet}'))
    if all(snippet in text for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            app_region,
            (
                'SvtAppContext* stagedAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                'if (!stagedAppData)',
                'return false;',
                'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData), sizeof(SvtAppContext), uint8_t(0));',
                'stagedAppData->svtHevcParams = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                'if (!stagedAppData->svtHevcParams)',
                'X265_FREE(stagedAppData);',
                'return false;',
                'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData->svtHevcParams), sizeof(EB_H265_ENC_CONFIGURATION), uint8_t(0));',
                'stagedAppData->dolbyVisionRpuCapacity = 0;',
                'stagedAppData->byteCount = 0;',
                'stagedAppData->outFrameCount = 0;',
                'encoder->m_svtAppData = stagedAppData;',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT app-context initialization must fully stage and zero-initialize the context before publishing encoder->m_svtAppData'))
        if not has_in_order(
            input_region,
            (
                'EB_BUFFERHEADERTYPE* stagedInputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                'if (!stagedInputPictureBuffer)',
                'return false;',
                'std::fill_n(reinterpret_cast<uint8_t*>(stagedInputPictureBuffer), sizeof(EB_BUFFERHEADERTYPE), uint8_t(0));',
                'EB_BUFFERHEADERTYPE *inputPtr = stagedInputPictureBuffer;',
                'inputPtr->pBuffer = (unsigned char*)x265_malloc(sizeof(EB_H265_ENC_INPUT));',
                'if (!inputPtr->pBuffer)',
                'X265_FREE(stagedInputPictureBuffer);',
                'return false;',
                'inputData->dolbyVisionRpu.payloadSize = 0;',
                'inputPtr->nSize = sizeof(EB_BUFFERHEADERTYPE);',
                'encoder->m_svtAppData->inputPictureBuffer = stagedInputPictureBuffer;',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT input-buffer initialization must fully stage the buffer before publishing encoder->m_svtAppData->inputPictureBuffer'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT app-context staging guardrails')
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

    print('SVT app-context staging validated')


if __name__ == '__main__':
    main()
