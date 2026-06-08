#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'for (int j = 0; j < m_numPools; j++)',
    'if (!m_threadPool[j].start())',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to start thread pool %d, aborting\\n", j);',
    'm_aborted = true;',
    'break;',
    'if (m_aborted)',
    'return;',
    'if (!m_scalingList.init())',
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
            failures.append((TARGET.as_posix(), 0, f'missing encoder threadpool start failure guardrail: {snippet}'))

    start_pos = text.find('for (int j = 0; j < m_numPools; j++)')
    fail_pos = text.find('if (!m_threadPool[j].start())', start_pos if start_pos != -1 else 0)
    abort_pos = text.find('m_aborted = true;', fail_pos if fail_pos != -1 else 0)
    break_pos = text.find('break;', abort_pos if abort_pos != -1 else 0)
    guard_pos = text.find('if (m_aborted)', break_pos if break_pos != -1 else 0)
    return_pos = text.find('return;', guard_pos if guard_pos != -1 else 0)
    scaling_pos = text.find('if (!m_scalingList.init())', return_pos if return_pos != -1 else 0)
    if -1 in (start_pos, fail_pos, abort_pos, break_pos, guard_pos, return_pos, scaling_pos) or not (
        start_pos < fail_pos < abort_pos < break_pos < guard_pos < return_pos < scaling_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Encoder::create must abort and return before continuing initialization when a thread pool fails to start'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder threadpool start failure handling guardrails')
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

    print('Encoder threadpool start failure handling validated')


if __name__ == '__main__':
    main()
