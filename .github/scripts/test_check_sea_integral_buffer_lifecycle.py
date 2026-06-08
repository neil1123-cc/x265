#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sea_integral_buffer_lifecycle.py')

# Coverage probes used by the scan for SEA integral-buffer lifecycle guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'FrameData must clear SEA integral ownership via destroySEAIntegralBuffers() before destroy() returns',
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


def valid_repo():
    return {
        'source/common/framedata.h': 'void destroySEAIntegralBuffers();\n',
        'source/common/framedata.cpp': '\n'.join((
            'void FrameData::destroySEAIntegralBuffers()',
            '{',
            '    if (m_meBuffer[i] != nullptr)',
            '    {',
            '        X265_FREE(m_meBuffer[i]);',
            '        m_meBuffer[i] = nullptr;',
            '    }',
            '    m_meIntegral[i] = nullptr;',
            '}',
            'void FrameData::destroy()',
            '{',
            '    destroySEAIntegralBuffers();',
            '}',
        )) + '\n',
        'source/encoder/dpb.cpp': 'curFrame->m_encData->destroySEAIntegralBuffers();\n',
        'source/encoder/encoder.cpp': '\n'.join((
            'frameEnc[layer]->m_encData->destroySEAIntegralBuffers();',
            'for (int i = 0; i < INTEGRAL_PLANE_NUM; i++)',
            '{',
            '    frameEnc[layer]->m_encData->m_meBuffer[i] = X265_MALLOC(uint32_t, needed);',
            '    if (frameEnc[layer]->m_encData->m_meBuffer[i])',
            '    {',
            '        continue;',
            '    }',
            '    frameEnc[layer]->m_encData->destroySEAIntegralBuffers();',
            '    m_aborted = true;',
            '    return -1;',
            '}',
        )) + '\n',
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_repo())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = valid_repo()
        repo['source/common/framedata.cpp'] = repo['source/common/framedata.cpp'].replace('m_meIntegral[i] = nullptr;', 'X265_FREE(m_meIntegral[i]);', 1)
        write_targets(root, repo)
        expect_fail(run_checker(root), 'forbidden SEA integral buffer lifecycle regression: X265_FREE(m_meIntegral[i]);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = valid_repo()
        repo['source/encoder/dpb.cpp'] = ''
        write_targets(root, repo)
        expect_fail(run_checker(root), 'missing SEA integral buffer lifecycle guardrail: curFrame->m_encData->destroySEAIntegralBuffers();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = valid_repo()
        repo['source/encoder/encoder.cpp'] = repo['source/encoder/encoder.cpp'].replace('    frameEnc[layer]->m_encData->destroySEAIntegralBuffers();\n    m_aborted = true;\n', '    m_aborted = true;\n', 1)
        write_targets(root, repo)
        expect_fail(run_checker(root), 'SEA integral plane allocation must clear stale state before allocation and roll back all planes before aborting encode')

    print('SEA integral buffer lifecycle tests passed')


if __name__ == '__main__':
    main()
