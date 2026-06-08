#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/sao.cpp')
REQUIRED_SNIPPETS = (
    'bool SAO::create(x265_param* param, int initCommon)',
    'CHECKED_MALLOC(m_tmpL1[i], pixel, m_param->maxCUSize + 1);',
    'CHECKED_MALLOC(m_tmpU[i], pixel, m_numCuInWidth * m_param->maxCUSize + 2 + 32);',
    'if (initCommon)',
    'CHECKED_MALLOC(m_depthSaoRate, double, 2 * SAO_DEPTHRATE_SIZE);',
    'CHECKED_MALLOC(m_clipTableBase,  pixel, maxY + 2 * rangeExt);',
    'return true;',
    'fail:',
    'destroy(initCommon);',
    'return false;',
)
FORBIDDEN_SNIPPETS = (
    'fail:\n    return false;',
)
REGION_START = 'bool SAO::create(x265_param* param, int initCommon)'
REGION_END = 'void SAO::createFromRootNode(SAO* root)'


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden SAO create rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing SAO create rollback guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'bool SAO::create(x265_param* param, int initCommon)',
                'CHECKED_MALLOC(m_tmpL1[i], pixel, m_param->maxCUSize + 1);',
                'CHECKED_MALLOC(m_tmpU[i], pixel, m_numCuInWidth * m_param->maxCUSize + 2 + 32);',
                'if (initCommon)',
                'CHECKED_MALLOC(m_depthSaoRate, double, 2 * SAO_DEPTHRATE_SIZE);',
                'CHECKED_MALLOC(m_clipTableBase,  pixel, maxY + 2 * rangeExt);',
                'return true;',
                'fail:',
                'destroy(initCommon);',
                'return false;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SAO::create must complete its staged allocation path before falling through to the shared destroy(initCommon) rollback'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SAO create rollback guardrails')
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

    print('SAO create rollback validated')


if __name__ == '__main__':
    main()
