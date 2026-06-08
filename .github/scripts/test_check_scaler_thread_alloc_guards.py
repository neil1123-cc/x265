#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaler_thread_alloc_guards.py')

# Coverage probes used by the scan for scaler thread allocation guardrails.
NORMALIZED_PROBES = (
    'Scaler::threadMain must validate the preallocated picture slot before dereferencing it',
    'forbidden scaler thread alloc regression: ',
    'missing scaler thread alloc guardrail: ',
    'Scaler::threadMain must guard frame-size-driven plane reallocation immediately after X265_MALLOC',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx])',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input picture slot\\n");',
                    '    m_parentEnc->m_ret = 4;',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                    'x265_picture* scaledPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
                    'if (!scaledPic->planes[0] || scaledPic->framesize != (size_t)frameSize)',
                    '{',
                    '    X265_FREE(scaledPic->planes[0]);',
                    '    scaledPic->planes[0] = X265_MALLOC(char, frameSize);',
                    '}',
                    'if (!scaledPic->planes[0])',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input plane\\n");',
                    '    scaledPic->planes[1] = nullptr;',
                    '    scaledPic->planes[2] = nullptr;',
                    '    scaledPic->planes[3] = nullptr;',
                    '    scaledPic->framesize = 0;',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx] = x265_picture_alloc();',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input picture\\n");',
                    'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWritten % QDepth]->planes[j] = X265_MALLOC(char, planesize[j]);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scaler thread alloc regression')

    print('Scaler thread allocation guard tests passed')


if __name__ == '__main__':
    main()
