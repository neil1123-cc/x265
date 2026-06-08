#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'dst = new (std::nothrow) VideoDesc(m_param->sourceWidth, m_param->sourceHeight, m_param->internalCsp, m_param->internalBitDepth);',
    'src = new (std::nothrow) VideoDesc(dstW, dstH, m_param->internalCsp, m_param->internalBitDepth);',
    'if (!src || !dst)',
    'delete src;',
    'delete dst;',
)
FORBIDDEN_SNIPPETS = (
    'dst = new VideoDesc(m_param->sourceWidth, m_param->sourceHeight, m_param->internalCsp, m_param->internalBitDepth);',
    'src = new VideoDesc(dstW, dstH, m_param->internalCsp, m_param->internalBitDepth);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR scaler VideoDesc alloc guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR scaler VideoDesc allocation pattern: {snippet}'))

    dst_pos = text.find('dst = new (std::nothrow) VideoDesc(')
    src_pos = text.find('src = new (std::nothrow) VideoDesc(', dst_pos)
    guard_pos = text.find('if (!src || !dst)', src_pos)
    if -1 in (dst_pos, src_pos, guard_pos) or not (dst_pos < src_pos < guard_pos):
        failures.append((TARGET.as_posix(), 0, 'ABR scaler VideoDesc allocations must use nothrow and feed the existing null guard'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR scaler VideoDesc allocation guards')
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

    print('ABR scaler VideoDesc allocation guards validated')


if __name__ == '__main__':
    main()
