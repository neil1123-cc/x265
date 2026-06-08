#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'if (code != 0x00000001)',
    'pic->rpu.payload[pic->rpu.payloadSize++] = byteVal;',
)
REQUIRED_SNIPPETS = (
    'int CLIOptions::rpuParser(x265_picture * pic)',
    'if (!pic || !pic->rpu.payload)',
    'uint8_t stagedPayload[1024];',
    'int stagedPayloadSize = 0;',
    'pic->rpu.payloadSize = 0;',
    'while (bytesRead++ < 4 && fread(&byteVal, sizeof(uint8_t), 1, dolbyVisionRpu))',
    'if (ferror(dolbyVisionRpu))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to read Dolby Vision RPU data for POC %d\\n", pic->pts);',
    'if (code != START_CODE)',
    'if (!stagedPayloadSize)',
    'if (!bytesLeft && !stagedPayloadSize)',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid Dolby Vision RPU startcode in POC %d\\n", pic->pts);',
    'if (bytesRead >= 1024)',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid Dolby Vision RPU size in POC %d\\n", pic->pts);',
    'stagedPayload[stagedPayloadSize++] = (code >> (3 * 8)) & 0xFF;',
    'std::memcpy(pic->rpu.payload, stagedPayload, stagedPayloadSize);',
    'pic->rpu.payloadSize = stagedPayloadSize;',
    'x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU not found for POC %d\\n", pic->pts);',
)
FORBIDDEN_SNIPPETS += (
    'pic->rpu.payload[pic->rpu.payloadSize++] = (code >> (3 * 8)) & 0xFF;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden Dolby Vision RPU parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing Dolby Vision RPU parse guardrail: {snippet}'))

    reset_pos = text.find('pic->rpu.payloadSize = 0;')
    first_read_pos = text.find('while (bytesRead++ < 4 && fread(&byteVal, sizeof(uint8_t), 1, dolbyVisionRpu))')
    first_ferror_pos = text.find('if (ferror(dolbyVisionRpu))', first_read_pos)
    main_loop_pos = text.find('while (fread(&byteVal, sizeof(uint8_t), 1, dolbyVisionRpu))', first_ferror_pos)
    second_ferror_pos = text.find('if (ferror(dolbyVisionRpu))', main_loop_pos)
    not_found_pos = text.find('x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU not found for POC %d\\n", pic->pts);', second_ferror_pos)
    if -1 in (reset_pos, first_read_pos, first_ferror_pos, main_loop_pos, second_ferror_pos, not_found_pos) or not (
        reset_pos < first_read_pos < first_ferror_pos < main_loop_pos < second_ferror_pos < not_found_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Dolby Vision RPU parsing must reset payload state and distinguish fread() failures from clean EOF/not-found handling'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Dolby Vision RPU parsing guardrails in x265cli.cpp')
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

    print('Dolby Vision RPU parse usage validated')


if __name__ == '__main__':
    main()
