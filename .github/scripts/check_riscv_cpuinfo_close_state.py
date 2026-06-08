#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/riscv64/cpu.h')
FORBIDDEN_SNIPPETS = (
    'if (ferror(file) || fclose(file))',
    'fclose(file);\n    return found;',
)
REQUIRED_SNIPPETS = (
    'else if (ferror(file)) {',
    'int closeFailed = ferror(file) != 0;',
    'if (fclose(file))',
    'closeFailed = 1;',
    'if (closeFailed)',
    'char line[1024];',
    'return 0;',
    'return found;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden riscv cpuinfo close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing riscv cpuinfo close guardrail: {snippet}'))
    if text.count('int closeFailed = ferror(file) != 0;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded RISC-V cpuinfo close paths'))
    if text.count('if (fclose(file))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded RISC-V cpuinfo fclose calls'))

    early_branch = text.find('else if (ferror(file)) {')
    line_buffer = text.find('char line[1024];')
    first_close = text.find('int closeFailed = ferror(file) != 0;')
    second_close = text.find('int closeFailed = ferror(file) != 0;', first_close + 1)
    return_found = text.rfind('return found;')
    if -1 not in (early_branch, line_buffer, first_close, second_close, return_found):
        if not (early_branch < first_close < line_buffer):
            failures.append((TARGET.as_posix(), 0, 'early RISC-V cpuinfo close guard moved out of the open-failure path'))
        if not (line_buffer < second_close < return_found):
            failures.append((TARGET.as_posix(), 0, 'final RISC-V cpuinfo close guard moved out of the read loop exit path'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check RISC-V cpuinfo close state')
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

    print('RISC-V cpuinfo close guard validated')


if __name__ == '__main__':
    main()
