#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_pos = text.find('x265_encoder *x265_encoder_open(x265_param *p)')
    fail_pos = text.find('encoder->m_paramBase[0] = PARAM_NS::x265_param_alloc();', func_pos if func_pos != -1 else 0)
    if func_pos == -1:
        return [(TARGET.as_posix(), 0, 'missing x265_encoder_open function')]

    failures = []
    snippets = (
        'Encoder* encoder = new (std::nothrow) Encoder;',
        'if (!encoder)',
        'x265_log(p, X265_LOG_ERROR, "Unable to allocate encoder instance\\n");',
        'return nullptr;',
        'encoder->m_paramBase[0] = PARAM_NS::x265_param_alloc();',
    )
    for snippet in snippets:
        if snippet not in text[func_pos:fail_pos + 80 if fail_pos != -1 else len(text)]:
            failures.append((TARGET.as_posix(), 0, f'missing x265_encoder_open allocation guardrail: {snippet}'))

    new_pos = text.find('Encoder* encoder = new (std::nothrow) Encoder;', func_pos)
    branch_pos = text.find('if (!encoder)', new_pos if new_pos != -1 else 0)
    log_pos = text.find('x265_log(p, X265_LOG_ERROR, "Unable to allocate encoder instance\\n");', branch_pos if branch_pos != -1 else 0)
    return_pos = text.find('return nullptr;', log_pos if log_pos != -1 else 0)
    alloc_pos = text.find('encoder->m_paramBase[0] = PARAM_NS::x265_param_alloc();', return_pos if return_pos != -1 else 0)
    if -1 in (new_pos, branch_pos, log_pos, return_pos, alloc_pos) or not (new_pos < branch_pos < log_pos < return_pos < alloc_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_encoder_open must reject encoder allocation failure before touching encoder-owned parameter storage'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_encoder_open allocation guard')
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

    print('x265_encoder_open allocation guard validated')


if __name__ == '__main__':
    main()
