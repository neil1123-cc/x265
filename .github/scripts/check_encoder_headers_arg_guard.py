#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, 'int x265_encoder_headers(x265_encoder *enc, x265_nal **pp_nal, uint32_t *pi_nal)')
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing x265_encoder_headers function')]

    failures = []
    snippets = (
        'if (!enc || !pp_nal)',
        'if (pi_nal)',
        '*pi_nal = 0;',
        'return -1;',
        'Encoder *encoder = static_cast<Encoder*>(enc);',
    )
    for snippet in snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing x265_encoder_headers argument guardrail: {snippet}'))

    branch_pos = func_text.find('if (!enc || !pp_nal)')
    pin_pos = func_text.find('if (pi_nal)', branch_pos if branch_pos != -1 else 0)
    zero_pos = func_text.find('*pi_nal = 0;', pin_pos if pin_pos != -1 else 0)
    return_pos = func_text.find('return -1;', zero_pos if zero_pos != -1 else 0)
    encoder_pos = func_text.find('Encoder *encoder = static_cast<Encoder*>(enc);', return_pos if return_pos != -1 else 0)
    if -1 in (branch_pos, pin_pos, zero_pos, return_pos, encoder_pos) or not (branch_pos < pin_pos < zero_pos < return_pos < encoder_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_encoder_headers must reject null NAL outputs before touching encoder state'))

    bad_abort = 'if (enc)\n    {\n        Encoder *encoder = static_cast<Encoder*>(enc);\n        encoder->m_aborted = true;\n    }'
    if bad_abort in func_text:
        failures.append((TARGET.as_posix(), 0, 'x265_encoder_headers must not abort the encoder for caller-owned output pointer errors'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_encoder_headers argument guard')
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

    print('x265_encoder_headers argument guard validated')


if __name__ == '__main__':
    main()
