#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/riscv64/cpu.h')
REQUIRED_SNIPPETS = (
    'FILE *file = fopen("/proc/cpuinfo", "r");',
    'else if (ferror(file)) {',
    'int closeFailed = ferror(file) != 0;',
    'if (fclose(file))',
    'closeFailed = 1;',
    'if (closeFailed)',
    'return 0;',
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
            failures.append((TARGET.as_posix(), 0, f'missing riscv cpuinfo open-state guardrail: {snippet}'))

    open_pos = text.find('FILE *file = fopen("/proc/cpuinfo", "r");')
    null_pos = text.find('if (file == nullptr)', open_pos)
    ferror_pos = text.find('else if (ferror(file)) {', null_pos)
    line_pos = text.find('char line[1024];', ferror_pos)
    if -1 in (open_pos, null_pos, ferror_pos, line_pos) or not (open_pos < null_pos < ferror_pos < line_pos):
        failures.append((TARGET.as_posix(), 0, 'riscv cpuinfo open-state guard must follow the null check before file reads'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check riscv cpuinfo open state')
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

    print('RISC-V cpuinfo open-state guard validated')


if __name__ == '__main__':
    main()
