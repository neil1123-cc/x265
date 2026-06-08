#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frame_alloc_encode_data_guards.py')

# Coverage probes used by the scan for Frame::allocEncodeData guardrails.
NORMALIZED_PROBES = (
    'Frame::allocEncodeData must fully initialize staged objects before publishing m_encData',
    'Encoder::encode must abort on Frame::allocEncodeData failure before dereferencing m_encData',
    'missing frame allocEncodeData guardrail: ',
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


def valid_frame_text():
    return '\n'.join((
        'bool Frame::allocEncodeData(x265_param *param, const SPS& sps)',
        '{',
        '    FrameData* stagedEncData = new (std::nothrow) FrameData;',
        '    PicYuv* stagedReconPic[NUM_RECON_VERSION] = { nullptr };',
        '    const bool sccEnabled = param->bEnableSCC != 0;',
        '    const int reconPicCount = sccEnabled ? 2 : 1;',
        '    for (int i = 0; i < reconPicCount; i++)',
        '    {',
        '        if (!stagedEncData)',
        '            goto fail;',
        '        stagedReconPic[i] = new (std::nothrow) PicYuv;',
        '        if (!stagedReconPic[i])',
        '            goto fail;',
        '    }',
        '    if (!stagedEncData->create(*param, sps, m_fencPic->m_picCsp))',
        '        goto fail;',
        '    if (!stagedReconPic[0]->create(param))',
        '        goto fail;',
        '    if (sccEnabled && !stagedReconPic[1]->create(param))',
        '        goto fail;',
        '    m_encData = stagedEncData;',
        '    for (int i = 0; i < reconPicCount; i++)',
        '    {',
        '        m_reconPic[i] = stagedReconPic[i];',
        '        m_encData->m_reconPic[i] = stagedReconPic[i];',
        '    }',
        '    return true;',
        'fail:',
        '    if (stagedEncData)',
        '    {',
        '        stagedEncData->destroy();',
        '        delete stagedEncData;',
        '    }',
        '    for (int i = 0; i < reconPicCount; i++)',
        '    {',
        '        if (stagedReconPic[i])',
        '        {',
        '            stagedReconPic[i]->destroy();',
        '            delete stagedReconPic[i];',
        '        }',
        '    }',
        '    return false;',
        '}',
    )) + '\n'


def valid_encoder_text():
    return '\n'.join((
        'if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))',
        '{',
        '    m_aborted = true;',
        '    x265_log(m_param, X265_LOG_ERROR, "memory allocation failure, aborting encode\\n");',
        '    return -1;',
        '}',
        'Slice* slice = frameEnc[layer]->m_encData->m_slice;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text(),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text().replace('    FrameData* stagedEncData = new (std::nothrow) FrameData;\n', '    m_encData = new FrameData;\n', 1),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden frame allocEncodeData regression: m_encData = new FrameData;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/frame.cpp': valid_frame_text(),
                'source/encoder/encoder.cpp': valid_encoder_text().replace('if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))\n{\n    m_aborted = true;\n    x265_log(m_param, X265_LOG_ERROR, "memory allocation failure, aborting encode\\n");\n    return -1;\n}\n', 'frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps);\n', 1),
            },
        )
        expect_fail(run_checker(root), 'missing Encoder::encode allocEncodeData guardrail: if (!frameEnc[layer]->allocEncodeData(m_reconfigure ? m_latestParam : m_param, m_sps))')

    print('Frame::allocEncodeData guard tests passed')


if __name__ == '__main__':
    main()
