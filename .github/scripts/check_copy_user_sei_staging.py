#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'auto clearUserSEI = [](x265_sei& userSEI)',
    'x265_sei stagedUserSEI = {};',
    'stagedUserSEI.payloads = new (std::nothrow) x265_sei_payload[numPayloads];',
    'clearUserSEI(stagedUserSEI);',
    'clearUserSEI(frame->m_userSEI);',
    'frame->m_userSEI = stagedUserSEI;',
    'stagedUserSEI.payloads = nullptr;',
    'stagedUserSEI.numPayloads = 0;',
)
FORBIDDEN_SNIPPETS = (
    'clearFrameUserSEI();',
    'if (frame->m_userSEI.payloads && numPayloads != frame->m_userSEI.numPayloads)\n        clearFrameUserSEI();',
    'if (frame->m_userSEI.payloads[i].payload && frame->m_userSEI.payloads[i].payloadSize < input.payloadSize)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden copyUserSEI staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing copyUserSEI staging guardrail: {snippet}'))

    staged_alloc_pos = text.find('stagedUserSEI.payloads = new (std::nothrow) x265_sei_payload[numPayloads];')
    clear_old_pos = text.find('clearUserSEI(frame->m_userSEI);')
    assign_pos = text.find('frame->m_userSEI = stagedUserSEI;')
    if -1 not in (staged_alloc_pos, clear_old_pos, assign_pos) and not (staged_alloc_pos < clear_old_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'copyUserSEI must build staged payloads before clearing and replacing the old frame state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check copyUserSEI staging guardrails')
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

    print('copyUserSEI staging validated')


if __name__ == '__main__':
    main()
