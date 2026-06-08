#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'OPT("pme")',
    'x265_log(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");',
    'OPT("pmode")',
    'x265_log(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
)
FORBIDDEN_SNIPPETS = (
    'x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n", optarg);',
    'x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n", optarg);',
    'x265_log_file(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");',
    'x265_log_file(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
    'x265_log(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n", optarg);',
    'x265_log(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n", optarg);',
)
REGION_START = 'OPT("pme")'
REGION_END = 'OPT("dolby-vision-rpu")'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


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
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing deprecated parallel log guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden deprecated parallel log regression: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        pme_start = region.find('OPT("pme")')
        pmode_start = region.find('OPT("pmode")', pme_start + 1)
        pme_block = region[pme_start:pmode_start] if -1 not in (pme_start, pmode_start) else ''
        pmode_block = region[pmode_start:] if pmode_start != -1 else ''
        if not has_in_order(
            pme_block,
            (
                'OPT("pme")',
                'x265_log(param, X265_LOG_ERROR, " pme feature is deprecated from release 4.1 \\n");',
                'return true;',
            ),
        ) or not has_in_order(
            pmode_block,
            (
                'OPT("pmode")',
                'x265_log(param, X265_LOG_ERROR, " pmode feature is deprecated from release 4.1 \\n");',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Deprecated pme/pmode handlers must emit their fixed deprecation messages inside the matching option blocks before returning'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check deprecated parallel option logging cleanup')
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

    print('Deprecated parallel option logging validated')


if __name__ == '__main__':
    main()
