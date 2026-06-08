#!/usr/bin/env python3
import argparse
from pathlib import Path


Y4M = Path('source/output/y4m.cpp')
YUV = Path('source/output/yuv.cpp')


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
    failures = []
    for relative, signature, alloc_line, log_line in (
        (Y4M, 'Y4MOutput::Y4MOutput(const char* filename, int w, int h, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int inputdepth)', 'buf = new (std::nothrow) char[width];', 'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M output row buffer\\n");'),
        (YUV, 'YUVOutput::YUVOutput(const char *filename, int w, int h, uint32_t d, int csp, int inputdepth)', 'buf = new (std::nothrow) char[width];', 'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV output row buffer\\n");'),
    ):
        path = repo_root / relative
        if not path.is_file():
            failures.append((relative.as_posix(), 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        func_text = extract_braced_block(text, signature)
        if not func_text:
            failures.append((relative.as_posix(), 0, f'missing constructor: {signature}'))
            continue
        required = (
            '#include <new>',
            alloc_line,
            'if (!buf)',
            log_line,
            'failed = true;',
            'return;',
        )
        for snippet in required:
            target_text = text if snippet == '#include <new>' else func_text
            if snippet not in target_text:
                failures.append((relative.as_posix(), 0, f'missing row-buffer allocation guardrail: {snippet}'))
        forbidden = 'buf = new char[width];'
        if forbidden in func_text:
            failures.append((relative.as_posix(), 0, f'forbidden row-buffer allocation regression: {forbidden}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Y4M/YUV row-buffer allocation guards')
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

    print('Y4M/YUV row-buffer allocation guards validated')


if __name__ == '__main__':
    main()
