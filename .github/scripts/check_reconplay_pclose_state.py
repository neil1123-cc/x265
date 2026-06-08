#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/reconplay.cpp')
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(outputPipe) != 0;',
    'if (pclose(outputPipe))',
    'if (closeFailed)',
    'pipeValid = false;',
    'outputPipe = nullptr;',
    'general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
    'general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
)


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
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing reconplay pclose guardrail: {snippet}'))
    if 'std::ferror(outputPipe) || pclose(outputPipe)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden reconplay short-circuit pclose regression'))

    dtor_text = extract_braced_block(text, 'ReconPlay::~ReconPlay()')
    if not dtor_text:
        failures.append((TARGET.as_posix(), 0, 'missing ReconPlay destructor'))
        return failures

    pipe_valid_pos = dtor_text.find('pipeValid = false;')
    close_state_pos = dtor_text.find('bool closeFailed = std::ferror(outputPipe) != 0;', pipe_valid_pos if pipe_valid_pos != -1 else 0)
    pclose_pos = dtor_text.find('if (pclose(outputPipe))', close_state_pos if close_state_pos != -1 else 0)
    warn_pos = dtor_text.find('general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");', pclose_pos if pclose_pos != -1 else 0)
    null_pos = dtor_text.find('outputPipe = nullptr;', warn_pos if warn_pos != -1 else 0)
    if -1 in (pipe_valid_pos, close_state_pos, pclose_pos, warn_pos, null_pos) or not (
        pipe_valid_pos < close_state_pos < pclose_pos < warn_pos < null_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ReconPlay destructor must clear pipeValid and outputPipe when finalizing the pipe'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reconplay pclose state')
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

    print('Reconplay pclose guard validated')


if __name__ == '__main__':
    main()
