#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/output.cpp')


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
    failures = []
    if '#include <new>' not in text:
        failures.append((TARGET.as_posix(), 0, 'missing output open allocation guardrail: #include <new>'))

    recon_text = extract_braced_block(text, 'ReconFile* ReconFile::open(const char *fname, int width, int height, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int sourceBitDepth)')
    output_text = extract_braced_block(text, 'OutputFile* OutputFile::open(const char *fname, InputFileInfo& inputInfo)')
    if not recon_text:
        failures.append((TARGET.as_posix(), 0, 'missing ReconFile::open function'))
    if not output_text:
        failures.append((TARGET.as_posix(), 0, 'missing OutputFile::open function'))
    if failures:
        return failures

    recon_required = (
        'new (std::nothrow) Y4MOutput',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M recon output\\n");',
        'new (std::nothrow) YUVOutput',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV recon output\\n");',
    )
    for snippet in recon_required:
        if snippet not in recon_text:
            failures.append((TARGET.as_posix(), 0, f'missing output open allocation guardrail: {snippet}'))

    output_required = (
        'new (std::nothrow) MKVOutput',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MKV output\\n");',
        'new (std::nothrow) MP4Output',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MP4 output\\n");',
        'new (std::nothrow) GOPOutput',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate GOP output\\n");',
        'new (std::nothrow) RAWOutput',
        'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\\n");',
    )
    for snippet in output_required:
        if snippet not in output_text:
            failures.append((TARGET.as_posix(), 0, f'missing output open allocation guardrail: {snippet}'))

    forbidden = (
        ('new Y4MOutput(', recon_text),
        ('new YUVOutput(', recon_text),
        ('new MKVOutput(', output_text),
        ('new MP4Output(', output_text),
        ('new GOPOutput(', output_text),
        ('new RAWOutput(', output_text),
    )
    for snippet, scope in forbidden:
        if snippet in scope:
            failures.append((TARGET.as_posix(), 0, f'forbidden output open allocation regression: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check output open allocation guards')
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

    print('Output open allocation guards validated')


if __name__ == '__main__':
    main()
