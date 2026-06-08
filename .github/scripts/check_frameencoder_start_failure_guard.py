#!/usr/bin/env python3
import argparse
from pathlib import Path


ENCODER_TARGET = Path('source/encoder/encoder.cpp')
FRAMEENCODER_TARGET = Path('source/encoder/frameencoder.cpp')
ENCODER_REQUIRED_SNIPPETS = (
    'if (!m_frameEncoder[i]->start())',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to start frame encoder thread %d, aborting\\n", i);',
    'm_frameEncoder[i]->m_threadActive.store(false);',
    'm_aborted = true;',
    'break;',
    'm_frameEncoder[i]->m_done.wait(); /* wait for thread to initialize */',
    'if (!m_frameEncoder[i]->m_threadActive.load())',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder thread %d, aborting\\n", i);',
    'if (m_aborted)',
    'return;',
)
FRAMEENCODER_REQUIRED_SNIPPETS = (
    'auto failThreadInit = [&](const char* message)',
    'm_tld = new (std::nothrow) ThreadLocalData[numTLD];',
    'if (!m_tld)',
    'failThreadInit("Unable to allocate frame encoder thread-local state\\n");',
    'if (!m_tld[i].analysis.initSearch(*m_param, m_top->m_scalingList))',
    'failThreadInit("Unable to allocate frame encoder search state\\n");',
    'if (!m_tld[i].analysis.create(m_tld))',
    'failThreadInit("Unable to allocate frame encoder analysis state\\n");',
    'm_tld = new (std::nothrow) ThreadLocalData;',
    'if (!m_tld->analysis.initSearch(*m_param, m_top->m_scalingList))',
    'if (!m_tld->analysis.create(nullptr))',
    'm_done.trigger();',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    encoder_path = repo_root / ENCODER_TARGET
    frameencoder_path = repo_root / FRAMEENCODER_TARGET
    if not encoder_path.is_file():
        return [(ENCODER_TARGET.as_posix(), 0, 'missing file')]
    if not frameencoder_path.is_file():
        return [(FRAMEENCODER_TARGET.as_posix(), 0, 'missing file')]

    encoder_text = encoder_path.read_text(encoding='utf-8', errors='ignore')
    frameencoder_text = frameencoder_path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in ENCODER_REQUIRED_SNIPPETS:
        if snippet not in encoder_text:
            failures.append((ENCODER_TARGET.as_posix(), 0, f'missing frame encoder start failure guardrail: {snippet}'))
    for snippet in FRAMEENCODER_REQUIRED_SNIPPETS:
        if snippet not in frameencoder_text:
            failures.append((FRAMEENCODER_TARGET.as_posix(), 0, f'missing frame encoder thread init guardrail: {snippet}'))

    start_fail_pos = encoder_text.find('if (!m_frameEncoder[i]->start())')
    abort_pos = encoder_text.find('m_aborted = true;', start_fail_pos if start_fail_pos != -1 else 0)
    break_pos = encoder_text.find('break;', abort_pos if abort_pos != -1 else 0)
    wait_pos = encoder_text.find('m_frameEncoder[i]->m_done.wait(); /* wait for thread to initialize */', start_fail_pos if start_fail_pos != -1 else 0)
    init_fail_pos = encoder_text.find('if (!m_frameEncoder[i]->m_threadActive.load())', wait_pos if wait_pos != -1 else 0)
    init_abort_pos = encoder_text.find('m_aborted = true;', init_fail_pos if init_fail_pos != -1 else 0)
    post_loop_abort_pos = encoder_text.find('if (m_aborted)', init_fail_pos if init_fail_pos != -1 else 0)
    post_loop_return_pos = encoder_text.find('return;', post_loop_abort_pos if post_loop_abort_pos != -1 else 0)
    if -1 in (start_fail_pos, abort_pos, break_pos, wait_pos) or not (start_fail_pos < abort_pos < break_pos < wait_pos):
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::create must abort and break out of frame encoder startup before waiting on m_done'))
    if -1 in (wait_pos, init_fail_pos, init_abort_pos, post_loop_abort_pos, post_loop_return_pos) or not (wait_pos < init_fail_pos < init_abort_pos < post_loop_abort_pos < post_loop_return_pos):
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::create must abort after thread initialization failures before continuing encoder startup'))

    pooled_alloc_pos = frameencoder_text.find('m_tld = new (std::nothrow) ThreadLocalData[numTLD];')
    pooled_alloc_guard_pos = frameencoder_text.find('if (!m_tld)', pooled_alloc_pos if pooled_alloc_pos != -1 else 0)
    pooled_init_guard_pos = frameencoder_text.find('if (!m_tld[i].analysis.initSearch(*m_param, m_top->m_scalingList))', pooled_alloc_guard_pos if pooled_alloc_guard_pos != -1 else 0)
    pooled_create_guard_pos = frameencoder_text.find('if (!m_tld[i].analysis.create(m_tld))', pooled_init_guard_pos if pooled_init_guard_pos != -1 else 0)
    pooled_signal_pos = frameencoder_text.find('failThreadInit("Unable to allocate frame encoder analysis state\\n");', pooled_create_guard_pos if pooled_create_guard_pos != -1 else 0)
    standalone_alloc_pos = frameencoder_text.find('m_tld = new (std::nothrow) ThreadLocalData;', pooled_signal_pos if pooled_signal_pos != -1 else 0)
    standalone_init_guard_pos = frameencoder_text.find('if (!m_tld->analysis.initSearch(*m_param, m_top->m_scalingList))', standalone_alloc_pos if standalone_alloc_pos != -1 else 0)
    standalone_create_guard_pos = frameencoder_text.find('if (!m_tld->analysis.create(nullptr))', standalone_init_guard_pos if standalone_init_guard_pos != -1 else 0)
    done_trigger_pos = frameencoder_text.find('m_done.trigger();     /* signal that thread is initialized */', standalone_create_guard_pos if standalone_create_guard_pos != -1 else 0)
    if -1 in (pooled_alloc_pos, pooled_alloc_guard_pos, pooled_init_guard_pos, pooled_create_guard_pos, pooled_signal_pos, standalone_alloc_pos, standalone_init_guard_pos, standalone_create_guard_pos, done_trigger_pos) or not (
        pooled_alloc_pos < pooled_alloc_guard_pos < pooled_init_guard_pos < pooled_create_guard_pos < pooled_signal_pos < standalone_alloc_pos < standalone_init_guard_pos < standalone_create_guard_pos < done_trigger_pos
    ):
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'FrameEncoder::threadMain must guard thread-local allocation, initSearch, and analysis.create before signaling startup completion'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check frame encoder start failure handling guardrails')
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

    print('Frame encoder start failure handling validated')


if __name__ == '__main__':
    main()
