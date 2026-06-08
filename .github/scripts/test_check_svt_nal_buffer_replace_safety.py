#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_nal_buffer_replace_safety.py')

# Coverage probes used by the scan for SVT NAL buffer replacement guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT NAL buffer replace regression: ',
    'missing SVT NAL buffer replace guardrail: ',
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
                    'static bool svt_copy_output_to_nal(Encoder* encoder, const EB_BUFFERHEADERTYPE* outputPtr)',
                    'if (outputPtr->nFilledLen > nalList.m_allocSize)',
                    'uint8_t* newBuffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
                    'if (!newBuffer)',
                    '    x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate output NAL buffer\\n");',
                    '    return false;',
                    'X265_FREE(nalList.m_buffer);',
                    'nalList.m_buffer = newBuffer;',
                    'nalList.m_allocSize = outputPtr->nFilledLen;',
                    'memcpy(nalList.m_buffer, outputPtr->pBuffer, outputPtr->nFilledLen);',
                    '#endif',
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
                    'uint8_t* buffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
                    'if (!buffer)',
                    'nalList.m_buffer = buffer;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT NAL buffer replace regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'static bool svt_copy_output_to_nal(Encoder* encoder, const EB_BUFFERHEADERTYPE* outputPtr)',
                    'if (outputPtr->nFilledLen > nalList.m_allocSize)',
                    'X265_FREE(nalList.m_buffer);',
                    'uint8_t* newBuffer = X265_MALLOC(uint8_t, outputPtr->nFilledLen);',
                    'if (!newBuffer)',
                    '    x265_log(encoder->m_param, X265_LOG_ERROR, "SVT HEVC encoder: unable to allocate output NAL buffer\\n");',
                    '    return false;',
                    'nalList.m_buffer = newBuffer;',
                    'nalList.m_allocSize = outputPtr->nFilledLen;',
                    'memcpy(nalList.m_buffer, outputPtr->pBuffer, outputPtr->nFilledLen);',
                    '#endif',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT NAL output replacement must allocate the new buffer before releasing and replacing nalList.m_buffer')

    print('SVT NAL buffer replace safety tests passed')


if __name__ == '__main__':
    main()
