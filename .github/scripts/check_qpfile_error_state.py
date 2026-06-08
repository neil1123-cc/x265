#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'if (!std::fgets(line, sizeof(line), qpfile))',
    'if (std::ferror(qpfile))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to read qpfile while parsing frame %d\\n", pic_org.poc);',
    'return false;',
    'break;',
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
            failures.append((TARGET.as_posix(), 0, f'missing qpfile error-state guardrail: {snippet}'))

    fgets_pos = text.find('if (!std::fgets(line, sizeof(line), qpfile))')
    ferror_pos = text.find('if (std::ferror(qpfile))', fgets_pos)
    log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to read qpfile while parsing frame %d\\n", pic_org.poc);', ferror_pos)
    return_pos = text.find('return false;', log_pos)
    break_pos = text.find('break;', return_pos)
    if -1 in (fgets_pos, ferror_pos, log_pos, return_pos, break_pos) or not (fgets_pos < ferror_pos < log_pos < return_pos < break_pos):
        failures.append((TARGET.as_posix(), 0, 'qpfile parsing must distinguish read errors from clean EOF before breaking'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check qpfile error state handling')
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

    print('QPFile error-state guard validated')


if __name__ == '__main__':
    main()
