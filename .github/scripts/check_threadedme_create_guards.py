#!/usr/bin/env python3
import argparse
from pathlib import Path


THREADEDME_TARGET = Path('source/encoder/threadedme.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')


def check_threadedme(repo_root):
    path = repo_root / THREADEDME_TARGET
    if not path.is_file():
        return [(THREADEDME_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    snippets = (
        'm_tld = new (std::nothrow) ThreadLocalData[m_tldCount];',
        'if (!m_tld)',
        'if (!m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList))',
        'if (!m_tld[i].analysis.create(m_tld))',
        'for (int j = 0; j <= i; j++)',
        'm_tld[j].destroy();',
        'delete[] m_tld;',
        'm_tld = nullptr;',
        'm_tldCount = 0;',
        'return false;',
    )
    for snippet in snippets:
        if snippet not in text:
            failures.append((THREADEDME_TARGET.as_posix(), 0, f'missing ThreadedME create guardrail: {snippet}'))

    order = [
        'm_tld = new (std::nothrow) ThreadLocalData[m_tldCount];',
        'if (!m_tld)',
        'if (!m_tld[i].analysis.initSearch(*m_param, m_enc.m_scalingList))',
        'if (!m_tld[i].analysis.create(m_tld))',
        'for (int j = 0; j <= i; j++)',
        'm_tld[j].destroy();',
        'delete[] m_tld;',
        'm_tld = nullptr;',
        'm_tldCount = 0;',
        'return false;',
    ]
    positions = []
    search_from = 0
    for snippet in order:
        pos = text.find(snippet, search_from)
        positions.append(pos)
        if pos != -1:
            search_from = pos
    if any(pos == -1 for pos in positions) or positions != sorted(positions):
        failures.append((THREADEDME_TARGET.as_posix(), 0, 'ThreadedME::create must reject allocation/init failures and roll back partial thread-local state'))

    return failures


def check_encoder(repo_root):
    path = repo_root / ENCODER_TARGET
    if not path.is_file():
        return [(ENCODER_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in (
        'if (!m_threadedME->create())',
        'delete m_threadedME;',
        'm_threadedME = nullptr;',
    ):
        if snippet not in text:
            failures.append((ENCODER_TARGET.as_posix(), 0, f'missing threadedME create cleanup guardrail: {snippet}'))

    branch_pos = text.find('if (!m_threadedME->create())')
    delete_pos = text.find('delete m_threadedME;', branch_pos if branch_pos != -1 else 0)
    null_pos = text.find('m_threadedME = nullptr;', delete_pos if delete_pos != -1 else 0)
    free_pos = text.find('X265_FREE(m_threadedME);', branch_pos if branch_pos != -1 else 0)
    if -1 in (branch_pos, delete_pos, null_pos) or not (branch_pos < delete_pos < null_pos) or free_pos != -1:
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::create must delete failed ThreadedME instances with delete, not X265_FREE'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    failures.extend(check_threadedme(repo_root))
    failures.extend(check_encoder(repo_root))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ThreadedME create guards')
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

    print('ThreadedME create guards validated')


if __name__ == '__main__':
    main()
