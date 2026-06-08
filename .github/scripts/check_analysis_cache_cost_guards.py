#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/analysis.cpp')
COMBINED_CONDITION = 'if ((m_param->bEnableRdRefine || m_param->bOptCUDeltaQP) && depth <= m_slice->m_pps->maxCuDQPDepth)'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'const bool needsCacheCost = m_param->bEnableRdRefine || m_param->bOptCUDeltaQP;',
        'if (needsCacheCost)',
        'cacheCost = X265_MALLOC(uint64_t, costArrSize);',
        'ok = cacheCost != nullptr;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing analysis cacheCost guardrail: {snippet}'))

    if text.count(COMBINED_CONDITION) < 2:
        failures.append((TARGET.as_posix(), 0, 'analysis cacheCost saves must cover both rd-refine and opt-cu-delta-qp paths in intra and inter code paths'))

    forbidden = 'if (m_param->bEnableRdRefine && depth <= m_slice->m_pps->maxCuDQPDepth)'
    if forbidden in text:
        failures.append((TARGET.as_posix(), 0, f'forbidden analysis cacheCost regression: {forbidden}'))

    create_pos = text.find('bool Analysis::create(ThreadLocalData *tld)')
    needs_pos = text.find('const bool needsCacheCost = m_param->bEnableRdRefine || m_param->bOptCUDeltaQP;', create_pos if create_pos != -1 else 0)
    if_pos = text.find('if (needsCacheCost)', needs_pos if needs_pos != -1 else 0)
    alloc_pos = text.find('cacheCost = X265_MALLOC(uint64_t, costArrSize);', if_pos if if_pos != -1 else 0)
    ok_pos = text.find('ok = cacheCost != nullptr;', alloc_pos if alloc_pos != -1 else 0)
    csp_pos = text.find('int csp = m_param->internalCsp;', ok_pos if ok_pos != -1 else 0)
    if -1 in (create_pos, needs_pos, if_pos, alloc_pos, ok_pos, csp_pos) or not (
        create_pos < needs_pos < if_pos < alloc_pos < ok_pos < csp_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Analysis::create must gate cacheCost allocation on rd-refine or opt-cu-delta-qp and include allocation success in the returned create status'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Analysis cacheCost allocation and save guards')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Analysis cacheCost guards validated')


if __name__ == '__main__':
    main()
