#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'FILE* toneMapFile = x265_fopen(p->toneMapFile, "r");',
    'if (!toneMapFile)',
    'bool closeFailed = std::ferror(toneMapFile) != 0;',
    'if (std::fclose(toneMapFile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(p, X265_LOG_ERROR, "Unable to close tone-map file.\\n");',
    'm_aborted = true;',
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
            failures.append((TARGET.as_posix(), 0, f'missing tone-map open-state guardrail: {snippet}'))

    open_pos = text.find('FILE* toneMapFile = x265_fopen(p->toneMapFile, "r");')
    null_pos = text.find('if (!toneMapFile)', open_pos)
    close_pos = text.find('bool closeFailed = std::ferror(toneMapFile) != 0;', null_pos)
    abort_pos = text.find('m_aborted = true;', close_pos)
    if -1 in (open_pos, null_pos, close_pos, abort_pos) or not (open_pos < null_pos < close_pos < abort_pos):
        failures.append((TARGET.as_posix(), 0, 'tone-map validation must close the file before marking the encoder aborted'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check tone-map file open state')
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

    print('Tone-map file open-state guard validated')


if __name__ == '__main__':
    main()
