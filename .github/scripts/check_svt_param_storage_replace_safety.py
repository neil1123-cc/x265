#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'void* zoneSvtHevcParam = param->rc.zones[i].zoneParam->svtHevcParam;',
    'memcpy(param->rc.zones[i].zoneParam, param, sizeof(x265_param));',
    'param->rc.zones[i].zoneParam->svtHevcParam = zoneSvtHevcParam;',
    'finalizeZoneParamCopy(param->rc.zones[i].zoneParam, param);',
    'if (param->svtHevcParam && !param->rc.zones[i].zoneParam->svtHevcParam)',
)
FORBIDDEN_SNIPPETS = (
    'dst->svtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
    'if (!dst->svtHevcParam)',
    'memcpy(dst->svtHevcParam, src->svtHevcParam, sizeof(EB_H265_ENC_CONFIGURATION));',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT param storage regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT param storage guardrail: {snippet}'))

    stage_pos = text.find(REQUIRED_SNIPPETS[0])
    memcpy_pos = text.find(REQUIRED_SNIPPETS[1])
    restore_pos = text.find(REQUIRED_SNIPPETS[2])
    finalize_pos = text.find(REQUIRED_SNIPPETS[3])
    guard_pos = text.find(REQUIRED_SNIPPETS[4])
    if -1 not in (stage_pos, memcpy_pos, restore_pos, finalize_pos, guard_pos):
        if not (stage_pos < memcpy_pos < restore_pos < finalize_pos < guard_pos):
            failures.append((
                TARGET.as_posix(),
                0,
                'SVT zone param storage must be staged before overwrite and validated after finalizeZoneParamCopy',
            ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT param storage replace safety guardrails')
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

    print('SVT param storage replace safety validated')


if __name__ == '__main__':
    main()
