#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_cache_cost_guards.py')

# Coverage probes used by the scan for analysis cacheCost allocation guardrails.
NORMALIZED_PROBES = (
    'analysis cacheCost saves must cover both rd-refine and opt-cu-delta-qp paths in intra and inter code paths',
    'Analysis::create must gate cacheCost allocation on rd-refine or opt-cu-delta-qp and include allocation success in the returned create status',
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


def valid_text():
    return '\n'.join((
        'bool Analysis::create(ThreadLocalData *tld)',
        '{',
        '    bool ok = true;',
        '    const bool needsCacheCost = m_param->bEnableRdRefine || m_param->bOptCUDeltaQP;',
        '    if (needsCacheCost)',
        '    {',
        '        cacheCost = X265_MALLOC(uint64_t, costArrSize);',
        '        ok = cacheCost != nullptr;',
        '    }',
        '    int csp = m_param->internalCsp;',
        '}',
        'uint64_t Analysis::compressIntraCU(const CUData& parentCTU, const CUGeom& cuGeom, int32_t qp)',
        '{',
        '    if ((m_param->bEnableRdRefine || m_param->bOptCUDeltaQP) && depth <= m_slice->m_pps->maxCuDQPDepth)',
        '    {',
        '        int cuIdx = (cuGeom.childOffset - 1) / 3;',
        '        cacheCost[cuIdx] = md.bestMode->rdCost;',
        '    }',
        '}',
        'SplitData Analysis::compressInterCU_rd5_6(const CUData& parentCTU, const CUGeom& cuGeom, int32_t qp)',
        '{',
        '    if ((m_param->bEnableRdRefine || m_param->bOptCUDeltaQP) && depth <= m_slice->m_pps->maxCuDQPDepth)',
        '    {',
        '        int cuIdx = (cuGeom.childOffset - 1) / 3;',
        '        cacheCost[cuIdx] = md.bestMode->rdCost;',
        '    }',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/analysis.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/analysis.cpp': valid_text().replace(
            'const bool needsCacheCost = m_param->bEnableRdRefine || m_param->bOptCUDeltaQP;',
            'const bool needsCacheCost = m_param->bEnableRdRefine;',
            1,
        )})
        expect_fail(run_checker(root), 'missing analysis cacheCost guardrail: const bool needsCacheCost = m_param->bEnableRdRefine || m_param->bOptCUDeltaQP;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/analysis.cpp': valid_text().replace(
            'ok = cacheCost != nullptr;',
            'ok = true;',
            1,
        )})
        expect_fail(run_checker(root), 'missing analysis cacheCost guardrail: ok = cacheCost != nullptr;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/analysis.cpp': valid_text().replace(
            'if ((m_param->bEnableRdRefine || m_param->bOptCUDeltaQP) && depth <= m_slice->m_pps->maxCuDQPDepth)',
            'if (m_param->bEnableRdRefine && depth <= m_slice->m_pps->maxCuDQPDepth)',
        )})
        expect_fail(run_checker(root), 'forbidden analysis cacheCost regression: if (m_param->bEnableRdRefine && depth <= m_slice->m_pps->maxCuDQPDepth)')

    print('Analysis cacheCost guard tests passed')


if __name__ == '__main__':
    main()
