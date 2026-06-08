#!/usr/bin/env python3
import argparse
from pathlib import Path


ENCODER_TARGET = Path('source/encoder/encoder.cpp')
FRAMEENCODER_TARGET = Path('source/encoder/frameencoder.cpp')
ENCODER_SNIPPETS = (
    'if (!m_threadedME->start())',
    'm_threadedME->stopJobs();',
    'm_param->bThreadedME = 0;',
    'x265_log(m_param, X265_LOG_ERROR, "Failed to start threadedME thread pool, --threaded-me disabled");',
)
FRAMEENCODER_SNIPPETS = (
    'if (m_top->m_threadedME && m_param->bThreadedME && !slice->isIntra())',
    'if (m_top->m_threadedME && m_param->bThreadedME && slice->m_sliceType != I_SLICE)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    encoder_path = repo_root / ENCODER_TARGET
    if not encoder_path.is_file():
        failures.append((ENCODER_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = encoder_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in ENCODER_SNIPPETS:
            if snippet not in text:
                failures.append((ENCODER_TARGET.as_posix(), 0, f'missing threadedME start failure guardrail: {snippet}'))

        start_pos = text.find('if (!m_threadedME->start())')
        stop_pos = text.find('m_threadedME->stopJobs();', start_pos if start_pos != -1 else 0)
        disable_pos = text.find('m_param->bThreadedME = 0;', stop_pos if stop_pos != -1 else 0)
        log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Failed to start threadedME thread pool, --threaded-me disabled");', disable_pos if disable_pos != -1 else 0)
        if -1 in (start_pos, stop_pos, disable_pos, log_pos) or not (start_pos < stop_pos < disable_pos < log_pos):
            failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::create must stop jobs and disable threadedME when its worker thread fails to start'))

    frameencoder_path = repo_root / FRAMEENCODER_TARGET
    if not frameencoder_path.is_file():
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = frameencoder_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in FRAMEENCODER_SNIPPETS:
            if snippet not in text:
                failures.append((FRAMEENCODER_TARGET.as_posix(), 0, f'missing threadedME frameencoder guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check threadedME start failure handling guardrails')
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

    print('ThreadedME start failure handling validated')


if __name__ == '__main__':
    main()
