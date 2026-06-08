#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sao_param_staging.py')


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
                'source/encoder/sao.cpp': '\n'.join((
                    'bool SAO::allocSaoParam(SAOParam* saoParam) const',
                    'if (!saoParam)',
                    'SaoCtuParam* stagedCtuParam[3] = { nullptr, nullptr, nullptr };',
                    'stagedCtuParam[i] = new (std::nothrow) SaoCtuParam[m_numCuInHeight * m_numCuInWidth];',
                    'delete[] stagedCtuParam[j];',
                    'saoParam->ctuParam[i] = stagedCtuParam[i];',
                    'bool SAO::startSlice(Frame* frame, Entropy& initState)',
                    '{',
                    'SAOParam* stagedSaoParam = new (std::nothrow) SAOParam;',
                    'if (!stagedSaoParam || !allocSaoParam(stagedSaoParam))',
                    '{',
                    'delete stagedSaoParam;',
                    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder SAO CTU state\\n");',
                    'return false;',
                    '}',
                    'saoParam = stagedSaoParam;',
                    'frame->m_encData->m_saoParam = saoParam;',
                    'return true;',
                    '}',
                )) + '\n',
                'source/encoder/sao.h': 'bool allocSaoParam(SAOParam* saoParam) const;\nbool startSlice(Frame* pic, Entropy& initState);\n',
                'source/encoder/framefilter.cpp': '\n'.join((
                    'if (m_useSao && !m_parallelFilter[row].m_sao.startSlice(frame, initState))',
                    '{',
                    '    m_useSao = 0;',
                    '    frame->m_encData->m_slice->m_bUseSao = 0;',
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
                'source/encoder/sao.cpp': '\n'.join((
                    'void SAO::allocSaoParam(SAOParam* saoParam) const',
                    'void SAO::startSlice(Frame* frame, Entropy& initState)',
                    'saoParam->ctuParam[i] = new SaoCtuParam[m_numCuInHeight * m_numCuInWidth];',
                    'saoParam = new SAOParam;',
                    'allocSaoParam(saoParam);',
                )) + '\n',
                'source/encoder/sao.h': 'void allocSaoParam(SAOParam* saoParam) const;\nvoid startSlice(Frame* pic, Entropy& initState);\n',
                'source/encoder/framefilter.cpp': 'if (m_useSao)\n    m_parallelFilter[row].m_sao.startSlice(frame, initState);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SAO param staging regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/sao.cpp': '\n'.join((
                    'bool SAO::allocSaoParam(SAOParam* saoParam) const',
                    'if (!saoParam)',
                    'SaoCtuParam* stagedCtuParam[3] = { nullptr, nullptr, nullptr };',
                    'stagedCtuParam[i] = new (std::nothrow) SaoCtuParam[m_numCuInHeight * m_numCuInWidth];',
                    'delete[] stagedCtuParam[j];',
                    'saoParam->ctuParam[i] = stagedCtuParam[i];',
                    'bool SAO::startSlice(Frame* frame, Entropy& initState)',
                    '{',
                    'SAOParam* stagedSaoParam = new (std::nothrow) SAOParam;',
                    'if (!stagedSaoParam || !allocSaoParam(stagedSaoParam))',
                    '{',
                    'delete stagedSaoParam;',
                    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder SAO CTU state\\n");',
                    'return false;',
                    '}',
                    'saoParam = stagedSaoParam;',
                    'frame->m_encData->m_saoParam = saoParam;',
                    'return true;',
                    '}',
                )) + '\n',
                'source/encoder/sao.h': 'bool allocSaoParam(SAOParam* saoParam) const;\nbool startSlice(Frame* pic, Entropy& initState);\n',
                'source/encoder/framefilter.cpp': 'if (m_useSao)\n    m_parallelFilter[row].m_sao.startSlice(frame, initState);\n',
            },
        )
        expect_fail(run_checker(root), 'missing SAO frame fallback guardrail: if (m_useSao && !m_parallelFilter[row].m_sao.startSlice(frame, initState))')

    print('SAO param staging tests passed')


if __name__ == '__main__':
    main()
