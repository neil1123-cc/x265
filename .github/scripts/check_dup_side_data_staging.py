#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'x265_picture stagedSideData = {};',
    'stagedSideData.userSEI.payloads = new (std::nothrow) x265_sei_payload[src->userSEI.numPayloads];',
    'clearDupPictureSideData(&stagedSideData);',
    'stagedSideData.rpu.payload = new (std::nothrow) uint8_t[src->rpu.payloadSize];',
    'clearDupPictureSideData(dest);',
    'dest->userSEI = stagedSideData.userSEI;',
    'dest->rpu = stagedSideData.rpu;',
    'stagedSideData.userSEI.payloads = nullptr;',
    'stagedSideData.rpu.payload = nullptr;',
)
FORBIDDEN_SNIPPETS = (
    'clearDupPictureSideData(dest);\n\n    if (src->userSEI.numPayloads < 0)',
    'clearDupPictureSideData(dest);\n                return false;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden dup side-data staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing dup side-data staging guardrail: {snippet}'))

    staged_pos = text.find('x265_picture stagedSideData = {};')
    clear_dest_pos = text.find('clearDupPictureSideData(dest);')
    assign_user_pos = text.find('dest->userSEI = stagedSideData.userSEI;')
    if -1 not in (staged_pos, clear_dest_pos, assign_user_pos) and not (staged_pos < clear_dest_pos < assign_user_pos):
        failures.append((TARGET.as_posix(), 0, 'dup side-data copy must stage new data before clearing and replacing dest state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check duplication side-data staging guardrails')
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

    print('Duplication side-data staging validated')


if __name__ == '__main__':
    main()
