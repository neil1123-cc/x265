#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_copyinfo_inter_arrays_guard.py')


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
                    'bool PassEncoder::copyInterAnalysis(x265_analysis_data* dstAnalysis, const x265_analysis_data* srcAnalysis)',
                    '{',
                    'if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter partition analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    'if (!interDst->interDir || !interSrc->interDir)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter direction analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    'if (!interDst->mvpIdx[dir] || !interSrc->mvpIdx[dir] ||',
                    '    !interDst->refIdx[dir] || !interSrc->refIdx[dir] ||',
                    '    !interDst->mv[dir] || !interSrc->mv[dir])',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing motion vector analysis buffers for encoder %u direction %d\\n", m_id, dir);',
                    '}',
                    'if (!interDst->ref || !interSrc->ref)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter reference analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'std::memcpy(interDst->mvpIdx[dir], interSrc->mvpIdx[dir], sizeof(uint8_t) * src->depthBytes);\n'})
        expect_fail(run_checker(root), 'missing ABR copyInfo inter-array guardrail: if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    'if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter partition analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    '}',
                    'bool PassEncoder::copyInterAnalysis(x265_analysis_data* dstAnalysis, const x265_analysis_data* srcAnalysis)',
                    '{',
                    'if (!interDst->interDir || !interSrc->interDir)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter direction analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    'if (!interDst->mvpIdx[dir] || !interSrc->mvpIdx[dir] ||',
                    '    !interDst->refIdx[dir] || !interSrc->refIdx[dir] ||',
                    '    !interDst->mv[dir] || !interSrc->mv[dir])',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing motion vector analysis buffers for encoder %u direction %d\\n", m_id, dir);',
                    '}',
                    'if (!interDst->ref || !interSrc->ref)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Missing inter reference analysis buffers for encoder %u\\n", m_id);',
                    '}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::copyInterAnalysis must guard deep inter analysis arrays before memcpy into them')

    print('ABR copyInfo inter-array guard tests passed')


if __name__ == '__main__':
    main()
