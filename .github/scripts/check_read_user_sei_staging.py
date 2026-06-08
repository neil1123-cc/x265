#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'SEIPayloadType stagedPayloadType;',
    'uint8_t* stagedPayload = (uint8_t*)x265_malloc(decodedSize);',
    'std::memcpy(stagedPayload, base64Decode, decodedSize);',
    'seiMsg.payloadSize = (int)decodedSize;',
    'seiMsg.payload = stagedPayload;',
    'seiMsg.payloadType = stagedPayloadType;',
)
FORBIDDEN_SNIPPETS = (
    'seiMsg.payloadSize = (int)decodedSize;\n                seiMsg.payload = (uint8_t*)x265_malloc(decodedSize);',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden readUserSei staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing readUserSei staging guardrail: {snippet}'))

    type_pos = text.find('SEIPayloadType stagedPayloadType;')
    alloc_pos = text.find('uint8_t* stagedPayload = (uint8_t*)x265_malloc(decodedSize);')
    assign_pos = text.find('seiMsg.payload = stagedPayload;')
    if -1 not in (type_pos, alloc_pos, assign_pos) and not (type_pos < alloc_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'readUserSeiFile must validate payload type and stage payload before committing seiMsg'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check readUserSeiFile staging guardrails')
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

    print('readUserSeiFile staging validated')


if __name__ == '__main__':
    main()
