#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.h')
FORBIDDEN_SNIPPETS = (
    '#define  x265_fclose(file) do { if ((file) != nullptr) { if (ferror(file) || fclose(file)) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n"); } file = nullptr; } while (0)',
)
REQUIRED_SNIPPETS = (
    '#define  x265_fclose(file) do {',
    'if ((file) != nullptr)',
    'bool closeFailed = ferror(file) != 0;',
    'if (fclose(file)) closeFailed = true;',
    'if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n");',
    'file = nullptr;',
    '} while (0)',
)
REGION_START = '/* Close a file */'
REGION_END = '#define x265_fread(val, size, readSize, fileOffset,errorMessage)\\'


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden x265_fclose macro close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing x265_fclose macro guardrail: {snippet}'))

    if region.count('#define  x265_fclose(file) do {') != 1:
        failures.append((TARGET.as_posix(), 0, 'x265_fclose macro guard must define exactly one close macro in the common.h close-file section'))

    if not has_in_order(
        region,
        (
            '#define  x265_fclose(file) do {',
            'if ((file) != nullptr)',
            'bool closeFailed = ferror(file) != 0;',
            'if (fclose(file)) closeFailed = true;',
            'if (closeFailed) x265_log(nullptr, X265_LOG_WARNING, "unable to finalize file state\\n");',
            'file = nullptr;',
            '} while (0)',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'x265_fclose macro must finalize the file state before clearing the pointer'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_fclose macro state')
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

    print('x265_fclose macro guard validated')


if __name__ == '__main__':
    main()
