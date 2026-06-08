#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'if (!bZoneParseError)',
    'x265_zone_free(p);',
    'p->rc.zoneCount = zoneCount;',
    'p->rc.zones = zones;',
)
FORBIDDEN_SNIPPETS = (
    'if (!bZoneParseError)\n        {\n            p->rc.zoneCount = zoneCount;\n            p->rc.zones = zones;\n        }',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden zone parse replacement regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing zone parse replacement guardrail: {snippet}'))

    clear_pos = text.find('x265_zone_free(p);')
    count_pos = text.find('p->rc.zoneCount = zoneCount;')
    assign_pos = text.find('p->rc.zones = zones;')
    if -1 not in (clear_pos, count_pos, assign_pos) and not (clear_pos < count_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'zone parse replacement must clear old zone state before assigning the new one'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zone parse replacement safety guardrails')
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

    print('Zone parse replacement safety validated')


if __name__ == '__main__':
    main()
