#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'if (inputPic[0]->quantOffsets != nullptr)',
    'copyUserSEIMessages(inFrame[0], inputPic[0]);',
    'if (inputPic[0]->rpu.payloadSize < 0)',
)
FORBIDDEN_SNIPPETS = (
    'if (inputPic[0]->rpu.payloadSize < 0)\n        {\n            x265_log(m_param, X265_LOG_ERROR, "Invalid Dolby Vision RPU payload size\\n");\n            return -1;\n        }\n\n        if (inputPic[0]->rpu.payloadSize)\n        {\n            if (!inputPic[0]->rpu.payload)\n            {\n                x265_log(m_param, X265_LOG_ERROR, "Dolby Vision RPU payload is null for non-zero payload size\\n");\n                return -1;\n            }\n\n            uint8_t* newRpuPayload = new (std::nothrow) uint8_t[inputPic[0]->rpu.payloadSize];\n            if (!newRpuPayload)\n            {\n                x265_log(m_param, X265_LOG_ERROR, "Unable to allocate Dolby Vision RPU payload buffer\\n");\n                return -1;\n            }\n            delete[] inFrame[0]->m_rpu.payload;\n            inFrame[0]->m_rpu.payload = newRpuPayload;\n            inFrame[0]->m_rpu.payloadSize = inputPic[0]->rpu.payloadSize;\n            std::memcpy(inFrame[0]->m_rpu.payload, inputPic[0]->rpu.payload, inputPic[0]->rpu.payloadSize);\n        }\n        else if (inFrame[0]->m_rpu.payload)\n        {\n            delete[] inFrame[0]->m_rpu.payload;\n            inFrame[0]->m_rpu.payload = nullptr;\n            inFrame[0]->m_rpu.payloadSize = 0;\n        }\n\n        if (inputPic[0]->quantOffsets != nullptr)',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden encode quantOffsets staging regression: {snippet[:80]}...'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encode quantOffsets staging guardrail: {snippet}'))

    quant_offsets_pos = text.find('if (inputPic[0]->quantOffsets != nullptr)')
    sei_pos = text.find('copyUserSEIMessages(inFrame[0], inputPic[0]);')
    rpu_pos = text.find('if (inputPic[0]->rpu.payloadSize < 0)')
    if -1 not in (quant_offsets_pos, sei_pos, rpu_pos) and not (quant_offsets_pos < sei_pos < rpu_pos):
        failures.append((TARGET.as_posix(), 0, 'encode must reject quantOffsets before copying user SEI messages and Dolby Vision RPU state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encode quantOffsets staging guardrails')
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

    print('encode quantOffsets staging validated')


if __name__ == '__main__':
    main()
