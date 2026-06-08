#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/frameencoder.cpp')
REQUIRED_SNIPPETS = (
    'Bitstream* stagedOutStreams = new (std::nothrow) Bitstream[numSubstreams];',
    'if (!stagedOutStreams)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream bitstreams\\n");',
    'm_top->m_aborted = true;',
    'Bitstream* stagedBackupStreams = nullptr;',
    'stagedBackupStreams = new (std::nothrow) Bitstream[numSubstreams];',
    'if (!stagedBackupStreams)',
    'delete[] stagedOutStreams;',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder backup substream bitstreams\\n");',
    'uint32_t* stagedSubstreamSizes = X265_MALLOC(uint32_t, numSubstreams);',
    'if (!stagedSubstreamSizes)',
    'delete[] stagedBackupStreams;',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder substream size table\\n");',
    'm_outStreams = stagedOutStreams;',
    'm_backupStreams = stagedBackupStreams;',
    'm_substreamSizes = stagedSubstreamSizes;',
)

FORBIDDEN_SNIPPETS = (
    'm_outStreams = new Bitstream[numSubstreams];',
    'm_backupStreams = new Bitstream[numSubstreams];',
    'm_substreamSizes = X265_MALLOC(uint32_t, numSubstreams);',
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
            failures.append((TARGET.as_posix(), 0, f'missing frameencoder substream allocation guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden frameencoder substream allocation regression: {snippet}'))

    alloc_pos = text.find('Bitstream* stagedOutStreams = new (std::nothrow) Bitstream[numSubstreams];')
    backup_alloc_pos = text.find('stagedBackupStreams = new (std::nothrow) Bitstream[numSubstreams];', alloc_pos if alloc_pos != -1 else 0)
    size_alloc_pos = text.find('uint32_t* stagedSubstreamSizes = X265_MALLOC(uint32_t, numSubstreams);', backup_alloc_pos if backup_alloc_pos != -1 else 0)
    assign_pos = text.find('m_outStreams = stagedOutStreams;', size_alloc_pos if size_alloc_pos != -1 else 0)
    if -1 in (alloc_pos, backup_alloc_pos, size_alloc_pos, assign_pos) or not (alloc_pos < backup_alloc_pos < size_alloc_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'FrameEncoder substream buffers must be staged and fully allocated before assignment to member state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check FrameEncoder substream allocation guardrails')
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

    print('FrameEncoder substream allocation guards validated')


if __name__ == '__main__':
    main()
