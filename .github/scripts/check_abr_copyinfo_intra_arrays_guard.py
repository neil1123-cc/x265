#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'copyIntraAnalysis(m_analysisInfo, src)',
    'if (!interDst->depth || !interSrc->depth || !interDst->modes || !interSrc->modes)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing inter analysis array buffers for encoder %u\\n", m_id);',
    'x265_log(m_param, X265_LOG_ERROR, "Missing inter cuTree analysis buffers for encoder %u\\n", m_id);',
    'x265_log(m_param, X265_LOG_ERROR, "Missing intra-in-inter analysis arrays for encoder %u\\n", m_id);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR copyInfo intra-array guardrail: {snippet}'))

    intra_copy_pos = text.find('copyIntraAnalysis(m_analysisInfo, src)')
    inter_arr_pos = text.find('if (!interDst->depth || !interSrc->depth || !interDst->modes || !interSrc->modes)', intra_copy_pos)
    intra_inter_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Missing intra-in-inter analysis arrays for encoder %u\\n", m_id);', inter_arr_pos)
    if -1 in (intra_copy_pos, inter_arr_pos, intra_inter_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInfo must guard intra/inter analysis arrays before memcpy into them'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::copyInfo intra-array guards')
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

    print('ABR copyInfo intra-array guards validated')


if __name__ == '__main__':
    main()
