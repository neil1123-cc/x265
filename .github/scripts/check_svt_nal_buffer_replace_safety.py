#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'static bool svt_copy_output_to_nal(Encoder* encoder, const EB_BUFFERHEADERTYPE* outputPtr)',
    'if (outputPtr->nFilledLen > nalList.m_allocSize)',
    'uint8_t* newBuffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
    'if (!newBuffer)',
    'x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate output NAL buffer\\n");',
    'return false;',
    'X265_FREE(nalList.m_buffer);',
    'nalList.m_buffer = newBuffer;',
    'nalList.m_allocSize = outputPtr->nFilledLen;',
    'memcpy(nalList.m_buffer, outputPtr->pBuffer, outputPtr->nFilledLen);',
)
FORBIDDEN_SNIPPETS = (
    'uint8_t* buffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
    'if (!buffer)',
    'nalList.m_buffer = buffer;',
)
REGION_START = 'static bool svt_copy_output_to_nal(Encoder* encoder, const EB_BUFFERHEADERTYPE* outputPtr)'
REGION_END = '#endif'


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
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT NAL buffer replace regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing SVT NAL buffer replace guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (outputPtr->nFilledLen > nalList.m_allocSize)',
                'uint8_t* newBuffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
                'if (!newBuffer)',
                'x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate output NAL buffer\\n");',
                'return false;',
                'X265_FREE(nalList.m_buffer);',
                'nalList.m_buffer = newBuffer;',
                'nalList.m_allocSize = outputPtr->nFilledLen;',
                'memcpy(nalList.m_buffer, outputPtr->pBuffer, outputPtr->nFilledLen);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT NAL output replacement must allocate the new buffer before releasing and replacing nalList.m_buffer'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT NAL buffer replace safety guardrails')
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

    print('SVT NAL buffer replace safety validated')


if __name__ == '__main__':
    main()
