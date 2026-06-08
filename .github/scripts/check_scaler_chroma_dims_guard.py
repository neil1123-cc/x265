#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/scaler.cpp')
REQUIRED_SNIPPETS = (
    'if (x265_cli_csps[srcCsp].planes <= 1)',
    'x265_log(nullptr, X265_LOG_ERROR, "scaler: monochrome ABR ladder scaling is unsupported\\n");',
    'if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)',
    'x265_log(nullptr, X265_LOG_ERROR, "scaler: chroma plane dimensions must remain positive after subsampling\\n");',
    'crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;',
    'crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;',
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
            failures.append((TARGET.as_posix(), 0, f'missing scaler chroma-dimension guardrail: {snippet}'))

    mono_guard_pos = text.find('if (x265_cli_csps[srcCsp].planes <= 1)')
    chroma_guard_pos = text.find('if (m_crSrcW <= 0 || m_crSrcH <= 0 || m_crDstW <= 0 || m_crDstH <= 0)', mono_guard_pos if mono_guard_pos != -1 else 0)
    crx_pos = text.find('crXInc = (((int64_t)m_crSrcW << 16) + (m_crDstW >> 1)) / m_crDstW;', chroma_guard_pos if chroma_guard_pos != -1 else 0)
    cry_pos = text.find('crYInc = (((int64_t)m_crSrcH << 16) + (m_crDstH >> 1)) / m_crDstH;', crx_pos if crx_pos != -1 else 0)
    if -1 in (mono_guard_pos, chroma_guard_pos, crx_pos, cry_pos) or not (
        mono_guard_pos < chroma_guard_pos < crx_pos < cry_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Scaler init must reject zero-sized chroma planes before chroma increment division'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaler chroma-dimension guardrails')
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

    print('Scaler chroma-dimension guards validated')


if __name__ == '__main__':
    main()
