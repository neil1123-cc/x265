#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET_CPP = Path('source/encoder/sao.cpp')
TARGET_H = Path('source/encoder/sao.h')
FRAMEFILTER_TARGET = Path('source/encoder/framefilter.cpp')
REQUIRED_CPP_SNIPPETS = (
    'bool SAO::allocSaoParam(SAOParam* saoParam) const',
    'if (!saoParam)',
    'SaoCtuParam* stagedCtuParam[3] = { nullptr, nullptr, nullptr };',
    'stagedCtuParam[i] = new (std::nothrow) SaoCtuParam[m_numCuInHeight * m_numCuInWidth];',
    'delete[] stagedCtuParam[j];',
    'saoParam->ctuParam[i] = stagedCtuParam[i];',
    'bool SAO::startSlice(Frame* frame, Entropy& initState)',
    'SAOParam* stagedSaoParam = new (std::nothrow) SAOParam;',
    'if (!stagedSaoParam || !allocSaoParam(stagedSaoParam))',
    'delete stagedSaoParam;',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder SAO CTU state\\n");',
    'return false;',
    'saoParam = stagedSaoParam;',
    'frame->m_encData->m_saoParam = saoParam;',
    'return true;',
)
FORBIDDEN_CPP_SNIPPETS = (
    'void SAO::allocSaoParam(SAOParam* saoParam) const',
    'void SAO::startSlice(Frame* frame, Entropy& initState)',
    'saoParam->ctuParam[i] = new SaoCtuParam[m_numCuInHeight * m_numCuInWidth];',
    'saoParam = new SAOParam;',
    'allocSaoParam(saoParam);',
)
REQUIRED_H_SNIPPETS = (
    'bool allocSaoParam(SAOParam* saoParam) const;',
    'bool startSlice(Frame* pic, Entropy& initState);',
)
REQUIRED_FRAMEFILTER_SNIPPETS = (
    'if (m_useSao && !m_parallelFilter[row].m_sao.startSlice(frame, initState))',
    'm_useSao = 0;',
    'frame->m_encData->m_slice->m_bUseSao = 0;',
)


def check_file(path, required, forbidden, label):
    if not path.is_file():
        return [(path.as_posix(), 0, f'missing {label} file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in forbidden:
        if snippet in text:
            failures.append((path.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
    for snippet in required:
        if snippet not in text:
            failures.append((path.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    failures.extend(check_file(repo_root / TARGET_CPP, REQUIRED_CPP_SNIPPETS, FORBIDDEN_CPP_SNIPPETS, 'SAO param staging'))
    failures.extend(check_file(repo_root / TARGET_H, REQUIRED_H_SNIPPETS, (), 'SAO param staging header'))
    failures.extend(check_file(repo_root / FRAMEFILTER_TARGET, REQUIRED_FRAMEFILTER_SNIPPETS, (), 'SAO frame fallback'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SAO param staging guardrails')
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

    print('SAO param staging validated')


if __name__ == '__main__':
    main()
