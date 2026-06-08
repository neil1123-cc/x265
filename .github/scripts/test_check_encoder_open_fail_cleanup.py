#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_open_fail_cleanup.py')

# Coverage probes used by the scan for encoder-open failure cleanup guardrails.
NORMALIZED_PROBES = (
    'x265_encoder_open must stop jobs and destroy a partially initialized encoder before falling back to manual param frees',
    'Encoder ctor and destroy must initialize and guard partial frame-duplication state for open-failure cleanup',
    'missing encoder partial-destroy guardrail: ',
    'missing file',
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
                    'fail:',
                    'if (encoder && encoder->m_param)',
                    '{',
                    '    encoder->stopJobs();',
                    '    encoder->destroy();',
                    '}',
                    'else',
                    '{',
                    '    PARAM_NS::x265_param_free(param);',
                    '    PARAM_NS::x265_param_free(latestParam);',
                    '    PARAM_NS::x265_param_free(zoneParam);',
                    '}',
                    'delete encoder;',
                )) + '\n',
                'source/encoder/encoder.cpp': '\n'.join((
                    'Encoder::Encoder()',
                    '{',
                    '    m_numPools = 0;',
                    '    m_bToneMap = 0;',
                    '    m_enableNal = 0;',
                    '    m_variance = nullptr;',
                    '    m_rdCost = nullptr;',
                    '    m_trainingCount = nullptr;',
                    '    zoneReadCount = nullptr;',
                    '    zoneWriteCount = nullptr;',
                    '    for (int i = 0; i < 3; i++)',
                    '    {',
                    '        m_dupPicOne[i] = nullptr;',
                    '        m_dupPicTwo[i] = nullptr;',
                    '    }',
                    '}',
                    'void Encoder::destroy()',
                    '{',
                    '    if (m_dupBuffer[i])',
                    '    {',
                    '        if (m_dupBuffer[i]->dupPic)',
                    '        {',
                    '            clearDupPictureSideData(m_dupBuffer[i]->dupPic);',
                    '            x265_picture_free(m_dupBuffer[i]->dupPic);',
                    '        }',
                    '    }',
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
                'source/encoder/api.cpp': 'fail:\nPARAM_NS::x265_param_free(param);\ndelete encoder;\n',
                'source/encoder/encoder.cpp': 'Encoder::Encoder()\n{\n}\nvoid Encoder::destroy()\n{\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing encoder-open fail cleanup guardrail: if (encoder && encoder->m_param)')

    print('Encoder-open failure cleanup tests passed')


if __name__ == '__main__':
    main()
