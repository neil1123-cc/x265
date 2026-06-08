#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reader_thread_alloc_guards.py')

# Coverage probes used by the scan for reader thread allocation guardrails.
NORMALIZED_PROBES = (
    'Reader::threadMain must guard src allocation before x265_picture_init',
    'Reader::threadMain must guard late plane allocation before memcpy',
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
                    'x265_picture* src = x265_picture_alloc();',
                    'if (!src)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input picture\\n");',
                    '    m_parentEnc->m_ret = 4;',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    return;',
                    '}',
                    'x265_picture_init(m_parentEnc->m_param, src);',
                    'if (!dest->planes[0])',
                    '{',
                    '    dest->planes[0] = X265_MALLOC(char, dest->framesize);',
                    '    if (!dest->planes[0])',
                    '    {',
                    '        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input plane\\n");',
                    '        m_parentEnc->m_ret = 4;',
                    '        m_threadActive.store(false);',
                    '        m_parentEnc->m_inputOver.store(true);',
                    '        m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '        break;',
                    '    }',
                    '}',
                    'std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));',
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
                    'x265_picture* src = x265_picture_alloc();',
                    'x265_picture_init(m_parentEnc->m_param, src);',
                    'dest->planes[0] = X265_MALLOC(char, dest->framesize);',
                    'std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing reader thread alloc guardrail: if (!src)')

    print('Reader thread allocation guard tests passed')


if __name__ == '__main__':
    main()
