#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_hdr10_json_metadata_ownership.py')

# Coverage probes used by the scan for HDR10 JSON metadata ownership guardrails.
NORMALIZED_PROBES = (
    'forbidden HDR10 metadata ownership regression: ',
    'missing HDR10 metadata ownership guardrail: ',
    'HDR10 metadata frame cleanup must release frame payloads before deleting the outer metadata array',
    'HDR10 movie metadata allocation must stage frame buffers before publishing the metadata array',
    'HDR10 frame metadata loading must replace the payload buffer before filling and publishing payload size',
    'HDR10 movie metadata loading must fill staged buffers before publishing the metadata array',
    'HDR10 extended frame metadata loading must replace the buffer before filling and backfilling payload bytes',
    'HDR10 extended movie metadata loading must finish staged frame payloads before publishing the metadata array',
    'HDR10 metadata clear must route positive frame counts through freeMetadataFrames',
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
                'source/dynamicHDR10/metadataFromJson.cpp': '\n'.join((
                    'const int kMetadataPayloadBytes = 509;',
                    'void freeMetadataFrames(uint8_t**& metadata, int count)',
                    '{',
                    'for (int i = 0; i < count; ++i)',
                    'delete[] metadata[i];',
                    'delete[] metadata;',
                    'metadata = nullptr;',
                    '}',
                    'bool replaceMetadataBuffer(uint8_t*& metadata, int size)',
                    '{',
                    'uint8_t* newMetadata = new (std::nothrow) uint8_t[size]();',
                    'if (!newMetadata)',
                    '    return false;',
                    'delete[] metadata;',
                    'metadata = newMetadata;',
                    'return true;',
                    '}',
                    'bool allocateMetadataFrames(uint8_t**& metadata, int numFrames, int frameSize)',
                    '{',
                    'uint8_t** stagedMetadata = new (std::nothrow) uint8_t*[numFrames]();',
                    'if (!stagedMetadata)',
                    '    return false;',
                    'stagedMetadata[frame] = new (std::nothrow) uint8_t[frameSize]();',
                    'if (!stagedMetadata[frame])',
                    'freeMetadataFrames(stagedMetadata, numFrames);',
                    '    return false;',
                    'metadata = stagedMetadata;',
                    'return true;',
                    '}',
                    'class metadataFromJson::DynamicMetaIO',
                    '{',
                    '};',
                    'bool metadataFromJson::frameMetadataFromJson(const char* filePath,',
                    '{',
                    'int mSEIBytesToRead = kMetadataPayloadBytes;',
                    'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                    '    return false;',
                    'fillMetadataArray(fileData, frame, jsonType, metadata);',
                    'mPimpl->setPayloadSize(metadata, 0, mPimpl->mCurrentStreamByte);',
                    'return true;',
                    '}',
                    'int metadataFromJson::movieMetadataFromJson(const char* filePath, uint8_t **&metadata)',
                    '{',
                    'uint8_t** stagedMetadata = nullptr;',
                    'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                    '    return -1;',
                    'fillMetadataArray(fileData, frame, jsonType, stagedMetadata[frame]);',
                    'mPimpl->setPayloadSize(stagedMetadata[frame], 0, mPimpl->mCurrentStreamByte);',
                    'metadata = stagedMetadata;',
                    'return numFrames;',
                    '}',
                    'bool metadataFromJson::extendedInfoFrameMetadataFromJson(const char* filePath,',
                    '{',
                    'int mSEIBytesToRead = kMetadataPayloadBytes;',
                    'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                    '    return false;',
                    'mPimpl->appendBits(metadata, extendedInfoframeType, 16);',
                    'fillMetadataArray(fileData, frame, LEGACY, metadata);',
                    'metadata[2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                    'metadata[3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                    'return true;',
                    '}',
                    'int metadataFromJson::movieExtendedInfoFrameMetadataFromJson(const char* filePath, uint8_t **&metadata)',
                    '{',
                    'uint8_t** stagedMetadata = nullptr;',
                    'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                    '    return -1;',
                    'mPimpl->appendBits(stagedMetadata[frame], extendedInfoframeType, 16);',
                    'fillMetadataArray(fileData, frame, LEGACY, stagedMetadata[frame]);',
                    'stagedMetadata[frame][2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                    'stagedMetadata[frame][3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                    'metadata = stagedMetadata;',
                    'return numFrames;',
                    '}',
                    'void metadataFromJson::fillMetadataArray',
                    '{',
                    '}',
                    'void metadataFromJson::clear(uint8_t **&metadata, const int numberOfFrames)',
                    '{',
                    'if (metadata && numberOfFrames > 0)',
                    'freeMetadataFrames(metadata, numberOfFrames);',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/metadataFromJson.cpp': '\n'.join((
                    'delete(metadata);',
                    'metadata = new uint8_t[mSEIBytesToRead];',
                    'metadata = new uint8_t*[numFrames];',
                    'std::memset(newMetadata, 0, size);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden HDR10 metadata ownership regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/dynamicHDR10/metadataFromJson.cpp': '\n'.join((
                    'const int kMetadataPayloadBytes = 509;',
                    'void freeMetadataFrames(uint8_t**& metadata, int count)',
                    '{',
                    'for (int i = 0; i < count; ++i)',
                    'delete[] metadata[i];',
                    'delete[] metadata;',
                    'metadata = nullptr;',
                    '}',
                    'bool replaceMetadataBuffer(uint8_t*& metadata, int size)',
                    '{',
                    'delete[] metadata;',
                    'uint8_t* newMetadata = new (std::nothrow) uint8_t[size]();',
                    'if (!newMetadata)',
                    '    return false;',
                    'metadata = newMetadata;',
                    'return true;',
                    '}',
                    'bool allocateMetadataFrames(uint8_t**& metadata, int numFrames, int frameSize)',
                    '{',
                    'uint8_t** stagedMetadata = new (std::nothrow) uint8_t*[numFrames]();',
                    'if (!stagedMetadata)',
                    '    return false;',
                    'stagedMetadata[frame] = new (std::nothrow) uint8_t[frameSize]();',
                    'if (!stagedMetadata[frame])',
                    '    freeMetadataFrames(stagedMetadata, numFrames);',
                    '    return false;',
                    'metadata = stagedMetadata;',
                    'return true;',
                    '}',
                    'class metadataFromJson::DynamicMetaIO',
                    '{',
                    '};',
                    'bool metadataFromJson::frameMetadataFromJson(const char* filePath,',
                    '{',
                    'int mSEIBytesToRead = kMetadataPayloadBytes;',
                    'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                    '    return false;',
                    'fillMetadataArray(fileData, frame, jsonType, metadata);',
                    'mPimpl->setPayloadSize(metadata, 0, mPimpl->mCurrentStreamByte);',
                    'return true;',
                    '}',
                    'int metadataFromJson::movieMetadataFromJson(const char* filePath, uint8_t **&metadata)',
                    '{',
                    'uint8_t** stagedMetadata = nullptr;',
                    'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                    '    return -1;',
                    'fillMetadataArray(fileData, frame, jsonType, stagedMetadata[frame]);',
                    'mPimpl->setPayloadSize(stagedMetadata[frame], 0, mPimpl->mCurrentStreamByte);',
                    'metadata = stagedMetadata;',
                    'return numFrames;',
                    '}',
                    'bool metadataFromJson::extendedInfoFrameMetadataFromJson(const char* filePath,',
                    '{',
                    'int mSEIBytesToRead = kMetadataPayloadBytes;',
                    'if (!replaceMetadataBuffer(metadata, mSEIBytesToRead))',
                    '    return false;',
                    'mPimpl->appendBits(metadata, extendedInfoframeType, 16);',
                    'fillMetadataArray(fileData, frame, LEGACY, metadata);',
                    'metadata[2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                    'metadata[3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                    'return true;',
                    '}',
                    'int metadataFromJson::movieExtendedInfoFrameMetadataFromJson(const char* filePath, uint8_t **&metadata)',
                    '{',
                    'uint8_t** stagedMetadata = nullptr;',
                    'if (!allocateMetadataFrames(stagedMetadata, numFrames, kMetadataPayloadBytes))',
                    '    return -1;',
                    'mPimpl->appendBits(stagedMetadata[frame], extendedInfoframeType, 16);',
                    'fillMetadataArray(fileData, frame, LEGACY, stagedMetadata[frame]);',
                    'stagedMetadata[frame][2] = (mPimpl->mCurrentStreamByte & 0xFF00) >> 8;',
                    'stagedMetadata[frame][3] = (mPimpl->mCurrentStreamByte & 0x00FF);',
                    'metadata = stagedMetadata;',
                    'return numFrames;',
                    '}',
                    'void metadataFromJson::fillMetadataArray',
                    '{',
                    '}',
                    'void metadataFromJson::clear(uint8_t **&metadata, const int numberOfFrames)',
                    '{',
                    'if (metadata && numberOfFrames > 0)',
                    'freeMetadataFrames(metadata, numberOfFrames);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'HDR10 single-frame metadata replacement must allocate the new buffer before releasing and replacing the old pointer')

    print('HDR10 JSON metadata ownership tests passed')


if __name__ == '__main__':
    main()
