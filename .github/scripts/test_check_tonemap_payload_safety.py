#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_tonemap_payload_safety.py')

# Coverage probes used by the scan for tone-map payload-safety guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing ',
    'copyUserSEIMessages must bound-check HDR10+ metadata, stage tone-map payloads safely, and append nalu/tone-map payloads after original user SEI payloads',
    'writeToneMapInfo must allocate replacement payload storage before dropping the old tone-map history payload',
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


def valid_encoder_text():
    return '\n'.join((
        'void Encoder::copyUserSEIMessages(Frame *frame, const x265_picture* pic_in)',
        '{',
        '    x265_sei_payload toneMap = {};',
        '    toneMap.payloadType = USER_DATA_REGISTERED_ITU_T_T35;',
        '    const int toneMapMetadataBytes = 509;',
        '    if (currentPOC >= 0 && currentPOC < m_numCimInfo && m_cim && m_cim[currentPOC])',
        '    {',
        '        while (payloadPrefixBytes < toneMapMetadataBytes && m_cim[currentPOC][payloadPrefixBytes] == 0xFF)',
        '        {',
        '            if (payloadSize > INT_MAX - 0xFF)',
        '            {',
        '                payloadSize = -1;',
        '                break;',
        '            }',
        '            payloadSize += 0xFF;',
        '            payloadPrefixBytes++;',
        '        }',
        '        if (payloadPrefixBytes >= toneMapMetadataBytes || payloadSize < 0 ||',
        '            payloadSize > INT_MAX - m_cim[currentPOC][payloadPrefixBytes])',
        '        {',
        '            x265_log(m_param, X265_LOG_ERROR, "Invalid HDR10+ tone-map payload prefix for frame %d\\n", currentPOC);',
        '        }',
        '        else if (payloadSize > toneMapMetadataBytes - payloadPrefixBytes - 1)',
        '        {',
        '            x265_log(m_param, X265_LOG_ERROR, "HDR10+ tone-map payload exceeds frame metadata buffer for frame %d\\n", currentPOC);',
        '        }',
        '        else if (payloadSize > 0)',
        '        {',
        '            uint8_t* stagedToneMapPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payloadSize);',
        '            if (!stagedToneMapPayload)',
        '            {',
        '                x265_log(m_param, X265_LOG_ERROR, "Unable to allocate HDR10+ tone-map payload buffer\\n");',
        '            }',
        '            else',
        '            {',
        '                toneMap.payload = stagedToneMapPayload;',
        '                toneMap.payloadSize = payloadSize;',
        '            }',
        '        }',
        '    }',
        '    for (int i = 0; i < numPayloads; i++)',
        '    {',
        '        if (i < pic_in->userSEI.numPayloads)',
        '            input = pic_in->userSEI.payloads[i];',
        '        else if (userPayload && i == pic_in->userSEI.numPayloads)',
        '            input = seiMsg;',
        '        else',
        '            input = toneMap;',
        '    }',
        '}',
    )) + '\n'


def valid_frameencoder_text():
    return '\n'.join((
        'bool FrameEncoder::writeToneMapInfo(x265_sei_payload *payload)',
        '{',
        '    if (payloadChange)',
        '    {',
        '        uint8_t* stagedPayload = nullptr;',
        '        stagedPayload = (uint8_t*)x265_malloc(sizeof(uint8_t) * payload->payloadSize);',
        '        if (!stagedPayload)',
        '        {',
        '            x265_log(m_param, X265_LOG_ERROR, "Unable to allocate tone-map payload history buffer\\n");',
        '            return true;',
        '        }',
        '        std::memcpy(stagedPayload, payload->payload, payload->payloadSize);',
        '        x265_free(m_top->m_prevTonemapPayload.payload);',
        '        m_top->m_prevTonemapPayload.payload = stagedPayload;',
        '    }',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': valid_encoder_text(),
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': valid_encoder_text().replace(
                    'while (payloadPrefixBytes < toneMapMetadataBytes && m_cim[currentPOC][payloadPrefixBytes] == 0xFF)',
                    'while (m_cim[currentPOC][i] == 0xFF)',
                    1,
                ),
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden tone-map payload safety regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': valid_encoder_text().replace(
                    '        else if (userPayload && i == pic_in->userSEI.numPayloads)\n'
                    '            input = seiMsg;\n'
                    '        else\n'
                    '            input = toneMap;\n',
                    '        else if (m_enableNal)\n'
                    '            input = seiMsg;\n'
                    '        else\n'
                    '            input = toneMap;\n',
                    1,
                ),
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden tone-map payload safety regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': valid_encoder_text(),
                'source/encoder/frameencoder.cpp': valid_frameencoder_text().replace(
                    '        x265_free(m_top->m_prevTonemapPayload.payload);\n'
                    '        m_top->m_prevTonemapPayload.payload = stagedPayload;\n',
                    '        m_top->m_prevTonemapPayload.payload = (uint8_t*)x265_malloc(sizeof(uint8_t)* payload->payloadSize);\n'
                    '        std::memcpy(m_top->m_prevTonemapPayload.payload, payload->payload, payload->payloadSize);\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden tone-map history replace safety regression')

    print('Tone-map payload safety tests passed')


if __name__ == '__main__':
    main()
