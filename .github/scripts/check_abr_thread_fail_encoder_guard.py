#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_encoder)',
    'api->encoder_get_stats(m_encoder, &stats, sizeof(stats));',
    'if (std::strlen(m_param->csvfn) && !b_ctrl_c)',
    'api->encoder_close(m_encoder);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread fail encoder guardrail: {snippet}'))

    fail_pos = text.find('fail:')
    guard_pos = text.find('if (m_encoder)', fail_pos)
    stats_pos = text.find('api->encoder_get_stats(m_encoder, &stats, sizeof(stats));', guard_pos)
    close_pos = text.find('api->encoder_close(m_encoder);', stats_pos)
    if -1 in (fail_pos, guard_pos, stats_pos, close_pos) or not (fail_pos < guard_pos < stats_pos < close_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain fail cleanup must guard m_encoder before stats/log/close'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain fail encoder guard')
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

    print('ABR thread fail encoder guard validated')


if __name__ == '__main__':
    main()
