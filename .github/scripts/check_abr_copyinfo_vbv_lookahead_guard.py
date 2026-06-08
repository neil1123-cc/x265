#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_param->bDisableLookahead && isVbv)',
    'if (!m_analysisInfo->lookahead.intraSatdForVbv || !src->lookahead.intraSatdForVbv ||',
    '!m_analysisInfo->lookahead.satdForVbv || !src->lookahead.satdForVbv ||',
    '!m_analysisInfo->lookahead.intraVbvCost || !src->lookahead.intraVbvCost ||',
    '!m_analysisInfo->lookahead.vbvCost || !src->lookahead.vbvCost)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing VBV lookahead analysis buffers for encoder %u\\n", m_id);',
    'std::memcpy(m_analysisInfo->lookahead.intraSatdForVbv, src->lookahead.intraSatdForVbv, src->numCuInHeight * sizeof(uint32_t));',
    'std::memcpy(m_analysisInfo->lookahead.vbvCost, src->lookahead.vbvCost, src->numCUsInFrame * sizeof(uint32_t));',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR copyInfo VBV lookahead guardrail: {snippet}'))

    branch_pos = text.find('if (m_param->bDisableLookahead && isVbv)')
    guard_pos = text.find('if (!m_analysisInfo->lookahead.intraSatdForVbv || !src->lookahead.intraSatdForVbv ||', branch_pos)
    copy_pos = text.find('std::memcpy(m_analysisInfo->lookahead.intraSatdForVbv, src->lookahead.intraSatdForVbv, src->numCuInHeight * sizeof(uint32_t));', guard_pos)
    if -1 in (branch_pos, guard_pos, copy_pos) or not (branch_pos < guard_pos < copy_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInfo must guard VBV lookahead buffers before copying them'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::copyInfo VBV lookahead guards')
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

    print('ABR copyInfo VBV lookahead guards validated')


if __name__ == '__main__':
    main()
