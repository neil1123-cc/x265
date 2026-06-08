#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'char *base64Decode = SEI::base64Decode(base64Encode, (int)base64EncodeLength, decodedString);',
    'bool stopReading = false;',
    'std::free(decodedString);',
    'if (stopReading)',
    'break;',
)
FORBIDDEN_SNIPPETS = (
    'if (base64Decode)\n            std::free(base64Decode);',
    'std::free(decodedString);\n                    break;',
    'std::free(decodedString);\n            break;',
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
            failures.append((TARGET.as_posix(), 0, f'missing readUserSei cleanup guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden readUserSei cleanup regression: {snippet}'))

    decode_pos = text.find('char *base64Decode = SEI::base64Decode(base64Encode, (int)base64EncodeLength, decodedString);')
    stop_pos = text.find('bool stopReading = false;', decode_pos)
    free_pos = text.find('std::free(decodedString);', decode_pos)
    break_pos = text.find('if (stopReading)', free_pos)
    if -1 not in (decode_pos, stop_pos, free_pos, break_pos) and not (decode_pos < stop_pos < free_pos < break_pos):
        failures.append((TARGET.as_posix(), 0, 'readUserSeiFile must free decodedString before breaking out of the loop'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check readUserSeiFile cleanup guardrails')
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

    print('readUserSeiFile cleanup validated')


if __name__ == '__main__':
    main()
