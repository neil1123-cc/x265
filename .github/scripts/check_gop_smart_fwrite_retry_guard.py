#!/usr/bin/env python3
import argparse
from pathlib import Path


GOP_H = Path('source/output/gop.h')
GOP_CPP = Path('source/output/gop.cpp')


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
    gop_h_path = repo_root / GOP_H
    gop_cpp_path = repo_root / GOP_CPP
    if not gop_h_path.is_file():
        return [(GOP_H.as_posix(), 0, 'missing file')]
    if not gop_cpp_path.is_file():
        return [(GOP_CPP.as_posix(), 0, 'missing file')]

    gop_h = gop_h_path.read_text(encoding='utf-8', errors='ignore')
    gop_cpp = gop_cpp_path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    header_required = 'bool smart_fwrite(const void* data, std::size_t size, FILE* file);'
    if header_required not in gop_h:
        failures.append((GOP_H.as_posix(), 0, f'missing GOP smart_fwrite retry guardrail: {header_required}'))
    if 'void smart_fwrite(const void* data, std::size_t size, FILE* file);' in gop_h:
        failures.append((GOP_H.as_posix(), 0, 'forbidden GOP smart_fwrite retry regression: void smart_fwrite(const void* data, std::size_t size, FILE* file);'))

    smart_fwrite_text = extract_braced_block(gop_cpp, 'bool GOPOutput::smart_fwrite(const void* data, std::size_t size, FILE* file)')
    if not smart_fwrite_text:
        failures.append((GOP_CPP.as_posix(), 0, 'missing GOPOutput::smart_fwrite function'))
        return failures

    required = (
        'int err = 0;',
        'err = errno ? errno : EIO;',
        'if (err == ENOSPC)',
        'clearerr(file);',
        'if (std::fseek(file, data_pos, SEEK_SET) == 0)',
        'return true;',
        'b_fail = true;',
        'return false;',
    )
    for snippet in required:
        if snippet not in smart_fwrite_text:
            failures.append((GOP_CPP.as_posix(), 0, f'missing GOP smart_fwrite retry guardrail: {snippet}'))

    forbidden = (
        'void GOPOutput::smart_fwrite(const void* data, std::size_t size, FILE* file)',
        'std::fseek(file, data_pos, SEEK_SET);',
    )
    for snippet in forbidden:
        if snippet in gop_cpp:
            failures.append((GOP_CPP.as_posix(), 0, f'forbidden GOP smart_fwrite retry regression: {snippet}'))

    err_pos = smart_fwrite_text.find('err = errno ? errno : EIO;')
    enospc_pos = smart_fwrite_text.find('if (err == ENOSPC)', err_pos if err_pos != -1 else 0)
    clearerr_pos = smart_fwrite_text.find('clearerr(file);', enospc_pos if enospc_pos != -1 else 0)
    seek_pos = smart_fwrite_text.find('if (std::fseek(file, data_pos, SEEK_SET) == 0)', clearerr_pos if clearerr_pos != -1 else 0)
    fail_pos = smart_fwrite_text.find('b_fail = true;', seek_pos if seek_pos != -1 else 0)
    if -1 in (err_pos, enospc_pos, clearerr_pos, seek_pos, fail_pos) or not (
        err_pos < enospc_pos < clearerr_pos < seek_pos < fail_pos
    ):
        failures.append((GOP_CPP.as_posix(), 0, 'GOPOutput::smart_fwrite must only retry after ENOSPC with clearerr() and fseek() success'))

    for snippet in (
        'if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))',
        'if (!smart_fwrite(&ts_lenx, 4, data_file) ||',
        'if (!smart_fwrite(p_nalu[i].payload, p_nalu[i].sizeBytes, data_file))',
    ):
        if snippet not in gop_cpp:
            failures.append((GOP_CPP.as_posix(), 0, f'missing GOP smart_fwrite retry guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP smart_fwrite retry guard')
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

    print('GOP smart_fwrite retry guard validated')


if __name__ == '__main__':
    main()
