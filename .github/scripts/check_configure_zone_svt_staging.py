#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'void* stagedZoneSvtHevcParam = zoneSvtHevcParam;',
    'if (p->svtHevcParam)',
    'if (!stagedZoneSvtHevcParam)',
    'stagedZoneSvtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
    'std::memcpy(stagedZoneSvtHevcParam, p->svtHevcParam, sizeof(EB_H265_ENC_CONFIGURATION));',
    'else if (stagedZoneSvtHevcParam)',
    'x265_free(stagedZoneSvtHevcParam);',
    'zone->svtHevcParam = stagedZoneSvtHevcParam;',
)
FORBIDDEN_SNIPPETS = (
    'std::memcpy(zone, p, sizeof(x265_param));\n    zone->logfn = nullptr;\n    zone->pgfn = nullptr;\n    zone->rc.zones = nullptr;\n    zone->rc.zoneCount = 0;\n    zone->rc.zonefileCount = 0;\n#ifdef SVT_HEVC\n    zone->svtHevcParam = zoneSvtHevcParam;\n    if (p->svtHevcParam)',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden configureZone SVT staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing configureZone SVT staging guardrail: {snippet}'))

    alloc_pos = text.find('stagedZoneSvtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));')
    memcpy_zone_pos = text.find('std::memcpy(zone, p, sizeof(x265_param));')
    assign_pos = text.find('zone->svtHevcParam = stagedZoneSvtHevcParam;')
    if -1 not in (alloc_pos, memcpy_zone_pos, assign_pos) and not (alloc_pos < memcpy_zone_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'configureZone must stage SVT storage before overwriting the zone object'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check configureZone SVT staging guardrails')
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

    print('configureZone SVT staging validated')


if __name__ == '__main__':
    main()
