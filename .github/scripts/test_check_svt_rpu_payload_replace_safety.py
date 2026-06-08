#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_rpu_payload_replace_safety.py')

# Coverage probes used by the scan for SVT RPU payload replacement guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT RPU payload replace regression: ',
    'missing SVT RPU payload replace guardrail: ',
    'SVT RPU payload clear path must drop the payload pointer before resetting capacity and payload size',
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
                    'if (pic_in->rpu.payloadSize)',
                    '{',
                    'if (encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
                    'uint8_t* newPayload = X265_MALLOC(uint8_t, payloadSize);',
                    'if (!newPayload)',
                    '    x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate Dolby Vision RPU payload buffer\\n");',
                    '    numEncoded = -1;',
                    '    goto fail;',
                    'X265_FREE(inputData->dolbyVisionRpu.payload);',
                    'inputData->dolbyVisionRpu.payload = newPayload;',
                    'encoder->m_svtAppData->dolbyVisionRpuCapacity = payloadSize;',
                    'memcpy(inputData->dolbyVisionRpu.payload, pic_in->rpu.payload, payloadSize);',
                    '}',
                    'else',
                    '{',
                    'if (inputData->dolbyVisionRpu.payload)',
                    '{',
                    'X265_FREE(inputData->dolbyVisionRpu.payload);',
                    'inputData->dolbyVisionRpu.payload = nullptr;',
                    'encoder->m_svtAppData->dolbyVisionRpuCapacity = 0;',
                    '}',
                    'inputData->dolbyVisionRpu.payloadSize = 0;',
                    '}',
                    'return_error = EbH265EncSendPicture(encoder->m_svtAppData->svtEncoderHandle, inputPtr);',
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
                    'if (inputData->dolbyVisionRpu.payload && encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
                    'inputData->dolbyVisionRpu.payload = X265_MALLOC(uint8_t, payloadSize);',
                    'inputData->dolbyVisionRpu.payload = nullptr;',
                    'encoder->m_svtAppData->dolbyVisionRpuCapacity = 0;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT RPU payload replace regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'if (pic_in->rpu.payloadSize)',
                    '{',
                    'if (encoder->m_svtAppData->dolbyVisionRpuCapacity < payloadSize)',
                    'X265_FREE(inputData->dolbyVisionRpu.payload);',
                    'uint8_t* newPayload = X265_MALLOC(uint8_t, payloadSize);',
                    'if (!newPayload)',
                    '    x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate Dolby Vision RPU payload buffer\\n");',
                    '    numEncoded = -1;',
                    '    goto fail;',
                    'inputData->dolbyVisionRpu.payload = newPayload;',
                    'encoder->m_svtAppData->dolbyVisionRpuCapacity = payloadSize;',
                    'memcpy(inputData->dolbyVisionRpu.payload, pic_in->rpu.payload, payloadSize);',
                    '}',
                    'else',
                    '{',
                    'if (inputData->dolbyVisionRpu.payload)',
                    '{',
                    'X265_FREE(inputData->dolbyVisionRpu.payload);',
                    'inputData->dolbyVisionRpu.payload = nullptr;',
                    'encoder->m_svtAppData->dolbyVisionRpuCapacity = 0;',
                    '}',
                    'inputData->dolbyVisionRpu.payloadSize = 0;',
                    '}',
                    'return_error = EbH265EncSendPicture(encoder->m_svtAppData->svtEncoderHandle, inputPtr);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT RPU payload replacement must allocate the new payload before releasing and replacing the prior payload buffer')

    print('SVT RPU payload replace safety tests passed')


if __name__ == '__main__':
    main()
