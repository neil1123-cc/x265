#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'if (zoneAllocCount && (!p->rc.zonefileCount || p->bResetZoneConfig))',
    'x265_copy_params(param, p);',
    'if (!param->bResetZoneConfig && param->rc.zonefileCount)',
    'param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
    'void* zoneSvtHevcParam = param->rc.zones[i].zoneParam->svtHevcParam;',
    'param->rc.zones[i].zoneParam->svtHevcParam = zoneSvtHevcParam;',
    'finalizeZoneParamCopy(param->rc.zones[i].zoneParam, param);',
    'if (param->svtHevcParam && !param->rc.zones[i].zoneParam->svtHevcParam)',
    'param->rc.zones[i].startFrame = -1;',
)
FORBIDDEN_SNIPPETS = (
    'if (zoneAllocCount)\n    {\n        param->rc.zoneCount = zoneAllocIsZoneFile ? 0 : p->rc.zoneCount;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden zone open staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing zone open staging guardrail: {snippet}'))

    copy_pos = text.find('x265_copy_params(param, p);')
    no_reset_pos = text.find('if (!param->bResetZoneConfig && param->rc.zonefileCount)')
    alloc_pos = text.find('param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);')
    if copy_pos == -1 or no_reset_pos == -1 or alloc_pos == -1:
        return failures

    if not (copy_pos < no_reset_pos < alloc_pos):
        failures.append((TARGET.as_posix(), 0, 'zone open staging order must remain copy -> no-reset branch -> zone allocation'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zone open staging guardrails')
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

    print('Zone open staging validated')


if __name__ == '__main__':
    main()
