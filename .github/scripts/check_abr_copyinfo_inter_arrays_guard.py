#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing inter partition analysis buffers for encoder %u\\n", m_id);',
    'if (!interDst->interDir || !interSrc->interDir)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing inter direction analysis buffers for encoder %u\\n", m_id);',
    'if (!interDst->mvpIdx[dir] || !interSrc->mvpIdx[dir] ||',
    '!interDst->refIdx[dir] || !interSrc->refIdx[dir] ||',
    '!interDst->mv[dir] || !interSrc->mv[dir])',
    'x265_log(m_param, X265_LOG_ERROR, "Missing motion vector analysis buffers for encoder %u direction %d\\n", m_id, dir);',
    'if (!interDst->ref || !interSrc->ref)',
    'x265_log(m_param, X265_LOG_ERROR, "Missing inter reference analysis buffers for encoder %u\\n", m_id);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR copyInfo inter-array guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
        brace_start = text.find('{', start)
        if brace_start == -1:
            return text[start:]
        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return text[start:]

    inter_text = extract_braced_block('bool PassEncoder::copyInterAnalysis(x265_analysis_data* dstAnalysis, const x265_analysis_data* srcAnalysis)')

    part_pos = inter_text.find('if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)')
    inter_dir_pos = inter_text.find('if (!interDst->interDir || !interSrc->interDir)', part_pos if part_pos != -1 else 0)
    mv_pos = inter_text.find('if (!interDst->mvpIdx[dir] || !interSrc->mvpIdx[dir] ||', inter_dir_pos if inter_dir_pos != -1 else 0)
    ref_pos = inter_text.find('if (!interDst->ref || !interSrc->ref)', mv_pos if mv_pos != -1 else 0)
    if -1 in (part_pos, inter_dir_pos, mv_pos, ref_pos) or not (part_pos < inter_dir_pos < mv_pos < ref_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::copyInterAnalysis must guard deep inter analysis arrays before memcpy into them'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::copyInterAnalysis inter-array guards')
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

    print('ABR copyInfo inter-array guards validated')


if __name__ == '__main__':
    main()
