#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_app_context_staging.py')

# Coverage probes used by the scan for SVT app-context staging guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT app-context staging regression: ',
    'missing SVT app-context staging guardrail: ',
    'SVT input-buffer initialization must fully stage the buffer before publishing encoder->m_svtAppData->inputPictureBuffer',
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
                'source/encoder/api.cpp': '\n'.join((
                    'bool svt_initialise_app_context(x265_encoder *enc)',
                    '{',
                    'SvtAppContext* stagedAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                    'if (!stagedAppData)',
                    '    return false;',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData), sizeof(SvtAppContext), uint8_t(0));',
                    'stagedAppData->svtHevcParams = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    'if (!stagedAppData->svtHevcParams)',
                    'X265_FREE(stagedAppData);',
                    '    return false;',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData->svtHevcParams), sizeof(EB_H265_ENC_CONFIGURATION), uint8_t(0));',
                    'stagedAppData->dolbyVisionRpuCapacity = 0;',
                    'stagedAppData->byteCount = 0;',
                    'stagedAppData->outFrameCount = 0;',
                    'encoder->m_svtAppData = stagedAppData;',
                    'return true;',
                    '}',
                    'bool svt_initialise_input_buffer(x265_encoder *enc)',
                    '{',
                    'EB_BUFFERHEADERTYPE* stagedInputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                    'if (!stagedInputPictureBuffer)',
                    '    return false;',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedInputPictureBuffer), sizeof(EB_BUFFERHEADERTYPE), uint8_t(0));',
                    'EB_BUFFERHEADERTYPE *inputPtr = stagedInputPictureBuffer;',
                    'inputPtr->pBuffer = (unsigned char*)x265_malloc(sizeof(EB_H265_ENC_INPUT));',
                    'if (!inputPtr->pBuffer)',
                    'X265_FREE(stagedInputPictureBuffer);',
                    '    return false;',
                    'inputData->dolbyVisionRpu.payloadSize = 0;',
                    'inputPtr->nSize = sizeof(EB_BUFFERHEADERTYPE);',
                    'encoder->m_svtAppData->inputPictureBuffer = stagedInputPictureBuffer;',
                    'return true;',
                    '}',
                    '#endif // ifdef SVT_HEVC',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'SvtAppContext* stagedAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                    'if (!stagedAppData)',
                    'stagedAppData->svtHevcParams = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    'X265_FREE(stagedAppData);',
                    'encoder->m_svtAppData = stagedAppData;',
                    'EB_BUFFERHEADERTYPE* stagedInputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                    'EB_BUFFERHEADERTYPE *inputPtr = stagedInputPictureBuffer;',
                    'X265_FREE(stagedInputPictureBuffer);',
                    'encoder->m_svtAppData->inputPictureBuffer = stagedInputPictureBuffer;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT app-context staging guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'encoder->m_svtAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                    'encoder->m_svtAppData->inputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                    'svt_release_app_context(encoder);',
                    '        return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT app-context staging regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'bool svt_initialise_app_context(x265_encoder *enc)',
                    '{',
                    'SvtAppContext* stagedAppData = (SvtAppContext*)x265_malloc(sizeof(SvtAppContext));',
                    'if (!stagedAppData)',
                    '    return false;',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData), sizeof(SvtAppContext), uint8_t(0));',
                    'stagedAppData->svtHevcParams = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    'if (!stagedAppData->svtHevcParams)',
                    '    return false;',
                    'X265_FREE(stagedAppData);',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedAppData->svtHevcParams), sizeof(EB_H265_ENC_CONFIGURATION), uint8_t(0));',
                    'stagedAppData->dolbyVisionRpuCapacity = 0;',
                    'stagedAppData->byteCount = 0;',
                    'stagedAppData->outFrameCount = 0;',
                    'encoder->m_svtAppData = stagedAppData;',
                    'return true;',
                    '}',
                    'bool svt_initialise_input_buffer(x265_encoder *enc)',
                    '{',
                    'EB_BUFFERHEADERTYPE* stagedInputPictureBuffer = (EB_BUFFERHEADERTYPE*)x265_malloc(sizeof(EB_BUFFERHEADERTYPE));',
                    'if (!stagedInputPictureBuffer)',
                    '    return false;',
                    'std::fill_n(reinterpret_cast<uint8_t*>(stagedInputPictureBuffer), sizeof(EB_BUFFERHEADERTYPE), uint8_t(0));',
                    'EB_BUFFERHEADERTYPE *inputPtr = stagedInputPictureBuffer;',
                    'inputPtr->pBuffer = (unsigned char*)x265_malloc(sizeof(EB_H265_ENC_INPUT));',
                    'if (!inputPtr->pBuffer)',
                    '    return false;',
                    'X265_FREE(stagedInputPictureBuffer);',
                    'inputData->dolbyVisionRpu.payloadSize = 0;',
                    'inputPtr->nSize = sizeof(EB_BUFFERHEADERTYPE);',
                    'encoder->m_svtAppData->inputPictureBuffer = stagedInputPictureBuffer;',
                    'return true;',
                    '}',
                    '#endif // ifdef SVT_HEVC',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT app-context initialization must fully stage and zero-initialize the context before publishing encoder->m_svtAppData')

    print('SVT app-context staging tests passed')


if __name__ == '__main__':
    main()
