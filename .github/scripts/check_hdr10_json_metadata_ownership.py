#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/dynamicHDR10/metadataFromJson.cpp')
REQUIRED_SNIPPETS = (
    'const int kMetadataPayloadBytes = 509;',
    'void freeMetadataFrames(uint8_t**& metadata, int count)',
    'delete[] metadata[i];',
    'delete[] metadata;',
    'metadata = nullptr;',
    'bool replaceMetadataBuffer(uint8_t*& metadata, int size)',
    'uint8_t* newMetadata = new (std::nothrow) uint8_t[size]();',
    'delete[] metadata;',
    'metadata = newMetadata;',
    'bool allocateMetadataFrames(uint8_t**& metadata, int numFrames, int frameSize)',
    'uint8_t** stagedMetadata = new (std::nothrow) uint8_t*[numFrames]();',
    'stagedMetadata[frame] = new (std::nothrow) uint8_t[frameSize]();',
    'freeMetadataFrames(stagedMetadata, numFrames);',
    'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
    'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
    'metadata = stagedMetadata;',
    'freeMetadataFrames(metadata, numberOfFrames);',
)
FORBIDDEN_SNIPPETS = (
    'delete(metadata);',
    'metadata = new uint8_t[mSEIBytesToRead];',
    'metadata = new uint8_t*[numFrames];',
    'metadata[frame] = new uint8_t[509];',
    'std::memset(newMetadata, 0, size);',
    'std::memset(stagedMetadata[frame], 0, frameSize);',
)
FREE_REGION_START = 'void freeMetadataFrames(uint8_t**& metadata, int count)'
FREE_REGION_END = 'bool replaceMetadataBuffer(uint8_t*& metadata, int size)'
REPLACE_REGION_START = 'bool replaceMetadataBuffer(uint8_t*& metadata, int size)'
REPLACE_REGION_END = 'bool allocateMetadataFrames(uint8_t**& metadata, int numFrames, int frameSize)'
ALLOC_REGION_START = 'bool allocateMetadataFrames(uint8_t**& metadata, int numFrames, int frameSize)'
ALLOC_REGION_END = 'class metadataFromJson::DynamicMetaIO'
FRAME_REGION_START = 'bool metadataFromJson::frameMetadataFromJson(const char* filePath,'
FRAME_REGION_END = 'int metadataFromJson::movieMetadataFromJson(const char* filePath, uint8_t **&metadata)'
MOVIE_REGION_START = 'int metadataFromJson::movieMetadataFromJson(const char* filePath, uint8_t **&metadata)'
MOVIE_REGION_END = 'bool metadataFromJson::extendedInfoFrameMetadataFromJson(const char* filePath,'
EXT_FRAME_REGION_START = 'bool metadataFromJson::extendedInfoFrameMetadataFromJson(const char* filePath,'
EXT_FRAME_REGION_END = 'int metadataFromJson::movieExtendedInfoFrameMetadataFromJson(const char* filePath, uint8_t **&metadata)'
EXT_MOVIE_REGION_START = 'int metadataFromJson::movieExtendedInfoFrameMetadataFromJson(const char* filePath, uint8_t **&metadata)'
EXT_MOVIE_REGION_END = 'void metadataFromJson::fillMetadataArray'
CLEAR_REGION_START = 'void metadataFromJson::clear(uint8_t **&metadata, const int numberOfFrames)'


def get_region(text, start_marker, end_marker=None):
    start = text.find(start_marker)
    if start == -1:
        return text
    if end_marker is None:
        return text[start:]
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return text[start:]
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
    free_region = get_region(text, FREE_REGION_START, FREE_REGION_END)
    replace_region = get_region(text, REPLACE_REGION_START, REPLACE_REGION_END)
    alloc_region = get_region(text, ALLOC_REGION_START, ALLOC_REGION_END)
    frame_region = get_region(text, FRAME_REGION_START, FRAME_REGION_END)
    movie_region = get_region(text, MOVIE_REGION_START, MOVIE_REGION_END)
    ext_frame_region = get_region(text, EXT_FRAME_REGION_START, EXT_FRAME_REGION_END)
    ext_movie_region = get_region(text, EXT_MOVIE_REGION_START, EXT_MOVIE_REGION_END)
    clear_region = get_region(text, CLEAR_REGION_START)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden HDR10 metadata ownership regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing HDR10 metadata ownership guardrail: {snippet}'))
    if all(snippet in text for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            free_region,
            (
                'for (int i = 0; i < count; ++i)',
                'delete[] metadata[i];',
                'delete[] metadata;',
                'metadata = nullptr;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 metadata frame cleanup must release frame payloads before deleting the outer metadata array'))
        if not has_in_order(
            replace_region,
            (
                'uint8_t* newMetadata = new (std::nothrow) uint8_t[size]();',
                'if (!newMetadata)',
                'return false;',
                'delete[] metadata;',
                'metadata = newMetadata;',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 single-frame metadata replacement must allocate the new buffer before releasing and replacing the old pointer'))
        if not has_in_order(
            alloc_region,
            (
                'uint8_t** stagedMetadata = new (std::nothrow) uint8_t*[numFrames]();',
                'if (!stagedMetadata)',
                'return false;',
                'stagedMetadata[frame] = new (std::nothrow) uint8_t[frameSize]();',
                'if (!stagedMetadata[frame])',
                'freeMetadataFrames(stagedMetadata, numFrames);',
                'return false;',
                'metadata = stagedMetadata;',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 movie metadata allocation must stage frame buffers before publishing the metadata array'))
        if not has_in_order(
            frame_region,
            (
                'int mSEIBytesToRead = kMetadataPayloadBytes;',
                'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                'return false;',
                'fillMetadataArray(fileData, frame, jsonType, metadata);',
                'mPimpl->setPayloadSize(metadata, 0, mPimpl->mCurrentStreamByte);',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 frame metadata loading must replace the payload buffer before filling and publishing payload size'))
        if not has_in_order(
            movie_region,
            (
                'uint8_t** stagedMetadata = nullptr;',
                'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                'return -1;',
                'fillMetadataArray(fileData, frame, jsonType, stagedMetadata[frame]);',
                'mPimpl->setPayloadSize(stagedMetadata[frame], 0, mPimpl->mCurrentStreamByte);',
                'metadata = stagedMetadata;',
                'return numFrames;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 movie metadata loading must fill staged buffers before publishing the metadata array'))
        if not has_in_order(
            ext_frame_region,
            (
                'int mSEIBytesToRead = kMetadataPayloadBytes;',
                'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                'return false;',
                'mPimpl->appendBits(metadata, extendedInfoframeType, 16);',
                'fillMetadataArray(fileData, frame, LEGACY, metadata);',
                'metadata[2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                'metadata[3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 extended frame metadata loading must replace the buffer before filling and backfilling payload bytes'))
        if not has_in_order(
            ext_movie_region,
            (
                'uint8_t** stagedMetadata = nullptr;',
                'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                'return -1;',
                'mPimpl->appendBits(stagedMetadata[frame], extendedInfoframeType, 16);',
                'fillMetadataArray(fileData, frame, LEGACY, stagedMetadata[frame]);',
                'stagedMetadata[frame][2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                'stagedMetadata[frame][3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                'metadata = stagedMetadata;',
                'return numFrames;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 extended movie metadata loading must finish staged frame payloads before publishing the metadata array'))
        if not has_in_order(
            clear_region,
            (
                'if (metadata && numberOfFrames > 0)',
                'freeMetadataFrames(metadata, numberOfFrames);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HDR10 metadata clear must route positive frame counts through freeMetadataFrames'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check HDR10 JSON metadata ownership guardrails')
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

    print('HDR10 JSON metadata ownership validated')


if __name__ == '__main__':
    main()
