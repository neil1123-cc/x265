#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/reconplay.cpp')
REQUIRED_SNIPPETS = (
    'pipeValid = true;',
    'threadActive.store(true);',
    'if (start())',
    'general_log(&param, "exec", X265_LOG_ERROR, "Unable to start recon playback thread\\n");',
    'threadActive.store(false);',
    'pipeValid = false;',
    'bool closeFailed = std::ferror(outputPipe) != 0;',
    'if (pclose(outputPipe))',
    'if (closeFailed)',
    'general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after thread start failure\\n");',
    'outputPipe = nullptr;',
    'goto fail;',
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
            failures.append((TARGET.as_posix(), 0, f'missing reconplay start failure guardrail: {snippet}'))

    start_pos = text.find('threadActive.store(true);')
    call_pos = text.find('if (start())', start_pos if start_pos != -1 else 0)
    log_pos = text.find('general_log(&param, "exec", X265_LOG_ERROR, "Unable to start recon playback thread\\n");', call_pos if call_pos != -1 else 0)
    reset_pos = text.find('pipeValid = false;', log_pos if log_pos != -1 else 0)
    close_pos = text.find('bool closeFailed = std::ferror(outputPipe) != 0;', reset_pos if reset_pos != -1 else 0)
    fail_pos = text.find('goto fail;', close_pos if close_pos != -1 else 0)
    if -1 in (start_pos, call_pos, log_pos, reset_pos, close_pos, fail_pos) or not (start_pos < call_pos < log_pos < reset_pos < close_pos < fail_pos):
        failures.append((TARGET.as_posix(), 0, 'ReconPlay constructor must reset thread state and close the pipe when thread startup fails'))
    if 'std::ferror(outputPipe) || pclose(outputPipe)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden reconplay thread-start short-circuit pclose regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reconplay start failure handling guardrails')
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

    print('Reconplay start failure handling validated')


if __name__ == '__main__':
    main()
