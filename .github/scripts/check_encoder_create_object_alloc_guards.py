#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'm_frameEncoder[i] = new (std::nothrow) FrameEncoder;',
        'if (!m_frameEncoder[i])',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder %d, aborting\\n", i);',
        'm_aborted = true;',
        'break;',
        'if (m_aborted)',
        'return;',
        'm_threadedME = new (std::nothrow) ThreadedME(m_param, *this);',
        'if (!m_threadedME)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate ThreadedME instance, aborting\\n");',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder create object alloc guardrail: {snippet}'))

    forbidden = (
        'm_frameEncoder[i] = new FrameEncoder;',
        'm_threadedME = new ThreadedME(m_param, *this);',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder create object alloc regression: {snippet}'))

    frame_alloc_pos = text.find('m_frameEncoder[i] = new (std::nothrow) FrameEncoder;')
    frame_guard_pos = text.find('if (!m_frameEncoder[i])', frame_alloc_pos if frame_alloc_pos != -1 else 0)
    frame_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder %d, aborting\\n", i);', frame_guard_pos if frame_guard_pos != -1 else 0)
    frame_break_pos = text.find('break;', frame_log_pos if frame_log_pos != -1 else 0)
    post_frame_abort_pos = text.find('if (m_aborted)', frame_break_pos if frame_break_pos != -1 else 0)
    post_frame_return_pos = text.find('return;', post_frame_abort_pos if post_frame_abort_pos != -1 else 0)
    threadedme_alloc_pos = text.find('m_threadedME = new (std::nothrow) ThreadedME(m_param, *this);', post_frame_return_pos if post_frame_return_pos != -1 else 0)
    threadedme_guard_pos = text.find('if (!m_threadedME)', threadedme_alloc_pos if threadedme_alloc_pos != -1 else 0)
    threadedme_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate ThreadedME instance, aborting\\n");', threadedme_guard_pos if threadedme_guard_pos != -1 else 0)
    if -1 in (frame_alloc_pos, frame_guard_pos, frame_log_pos, frame_break_pos, post_frame_abort_pos, post_frame_return_pos, threadedme_alloc_pos, threadedme_guard_pos, threadedme_log_pos) or not (
        frame_alloc_pos < frame_guard_pos < frame_log_pos < frame_break_pos < post_frame_abort_pos < post_frame_return_pos < threadedme_alloc_pos < threadedme_guard_pos < threadedme_log_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Encoder::create must reject FrameEncoder and ThreadedME allocation failures before using those objects'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Encoder::create object allocation guards')
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

    print('Encoder::create object allocation guards validated')


if __name__ == '__main__':
    main()
