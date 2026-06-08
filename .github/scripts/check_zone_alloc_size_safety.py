#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
    'if (zoneCount <= 0)',
    'if ((size_t)zoneCount > SIZE_MAX / sizeof(x265_zone))',
    'x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
    'if (!zone)',
    'std::fill_n(zone, zoneCount, x265_zone());',
    'if (isZoneFile)',
    'for (int i = 0; i < zoneCount; i++)',
    'zone[i].zoneParam = x265_param_alloc();',
    'if (!zone[i].zoneParam)',
    'for (int j = 0; j < i; j++)',
    'PARAM_NS::x265_param_free(zone[j].zoneParam);',
    'x265_free(zone);',
    'return zone;',
)
FORBIDDEN_SNIPPETS = (
    'if ((size_t)zoneCount >= SIZE_MAX / sizeof(x265_zone))',
)
REGION_START = 'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)'
REGION_END = 'void x265_zone_free(x265_param *param)'


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
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden zone alloc size regression: {snippet}'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing zone alloc size guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
                'if (zoneCount <= 0)',
                'if ((size_t)zoneCount > SIZE_MAX / sizeof(x265_zone))',
                'x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
                'if (!zone)',
                'std::fill_n(zone, zoneCount, x265_zone());',
                'if (isZoneFile)',
                'for (int i = 0; i < zoneCount; i++)',
                'zone[i].zoneParam = x265_param_alloc();',
                'if (!zone[i].zoneParam)',
                'for (int j = 0; j < i; j++)',
                'PARAM_NS::x265_param_free(zone[j].zoneParam);',
                'x265_free(zone);',
                'return zone;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'x265_zone_alloc must preserve the reviewed size guards and zoneParam rollback ordering before returning an allocated zone array'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_zone_alloc size safety guardrails')
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

    print('Zone alloc size safety validated')


if __name__ == '__main__':
    main()
