#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'bool bBitrateValueError = false;',
    'int bitrate = parseOptionIntValue(value, bBitrateValueError);',
    'bError |= bBitrateValueError;',
    'if (!bBitrateValueError)',
    'p->rc.bitrate = bitrate;',
    'p->rc.rateControlMode = X265_RC_ABR;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if text.count('p->rc.bitrate = x265_atoi(value, bError);\n        p->rc.rateControlMode = X265_RC_ABR;') != 0:
        failures.append((TARGET.as_posix(), 0, 'forbidden bitrate mode regression: invalid bitrate must not switch rate control mode'))
        return failures

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
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

    def extract_option_block(function_text, option_name, required_inner_snippet=None):
        search_from = 0
        needle = f'OPT("{option_name}")'
        while True:
            start = function_text.find(needle, search_from)
            if start == -1:
                return function_text
            next_opt = function_text.find('OPT("', start + len(needle))
            brace_start = function_text.find('{', start + len(needle))
            if brace_start != -1 and (next_opt == -1 or brace_start < next_opt):
                depth = 0
                for idx in range(brace_start, len(function_text)):
                    char = function_text[idx]
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            block = function_text[start:idx + 1]
                            if required_inner_snippet is None or required_inner_snippet in block:
                                return block
                            break
                else:
                    block = function_text[start:]
                    if required_inner_snippet is None or required_inner_snippet in block:
                        return block
            search_from = start + len(needle)

    def validate_bitrate_block(function_name, function_text):
        block = extract_option_block(function_text, 'bitrate', 'p->rc.rateControlMode = X265_RC_ABR;')
        for snippet in REQUIRED_SNIPPETS:
            if snippet not in block:
                failures.append((TARGET.as_posix(), 0, f'missing bitrate mode guardrail in {function_name} parse block: {snippet}'))

        parse_pos = block.find('int bitrate = parseOptionIntValue(value, bBitrateValueError);')
        error_pos = block.find('bError |= bBitrateValueError;', parse_pos if parse_pos != -1 else 0)
        guard_pos = block.find('if (!bBitrateValueError)', error_pos if error_pos != -1 else 0)
        assign_pos = block.find('p->rc.bitrate = bitrate;', guard_pos if guard_pos != -1 else 0)
        mode_pos = block.find('p->rc.rateControlMode = X265_RC_ABR;', assign_pos if assign_pos != -1 else 0)
        if -1 in (parse_pos, error_pos, guard_pos, assign_pos, mode_pos) or not (parse_pos < error_pos < guard_pos < assign_pos < mode_pos):
            failures.append((TARGET.as_posix(), 0, f'{function_name} bitrate parse block must gate ABR mode switch on parseOptionIntValue success'))

    scenecut_text = extract_braced_block('int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)')
    param_text = extract_braced_block('int x265_param_parse(x265_param* p, const char* name, const char* value)')
    validate_bitrate_block('x265_scenecut_aware_qp_param_parse', scenecut_text)
    validate_bitrate_block('x265_param_parse', param_text)
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check bitrate mode parse safety guardrails')
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

    print('Bitrate mode parse safety validated')


if __name__ == '__main__':
    main()
