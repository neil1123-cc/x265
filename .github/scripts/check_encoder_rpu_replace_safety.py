#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'uint8_t* newRpuPayload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];',
    'if (!newRpuPayload)',
    'delete[] inFrame[0]->m_rpu.payload;',
    'inFrame[0]->m_rpu.payload = newRpuPayload;',
    'else if (inFrame[0]->m_rpu.payload)',
    'inFrame[0]->m_rpu.payload = nullptr;',
    'inFrame[0]->m_rpu.payloadSize = 0;',
)
FORBIDDEN_SNIPPETS = (
    'if (inFrame[0]->m_rpu.payload)\n        {\n            delete[] inFrame[0]->m_rpu.payload;\n            inFrame[0]->m_rpu.payload = nullptr;\n            inFrame[0]->m_rpu.payloadSize = 0;\n        }\n\n        if (inputPic[0]->rpu.payloadSize)',
    'inFrame[0]->m_rpu.payload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder RPU replacement regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder RPU replacement guardrail: {snippet}'))

    alloc_pos = text.find('uint8_t* newRpuPayload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];')
    delete_pos = text.find('delete[] inFrame[0]->m_rpu.payload;')
    assign_pos = text.find('inFrame[0]->m_rpu.payload = newRpuPayload;')
    if -1 not in (alloc_pos, delete_pos, assign_pos) and not (alloc_pos < delete_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'encoder RPU replacement must allocate before dropping the old payload'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder RPU replacement safety guardrails')
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

    print('Encoder RPU replacement safety validated')


if __name__ == '__main__':
    main()
