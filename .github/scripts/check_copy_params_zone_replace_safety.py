#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'void x265_copy_params(x265_param* dst, x265_param* src)',
    'const bool preserveDstZones = (src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig) ||',
    '(src->rc.zoneCount && src->rc.zones);',
    'const bool zonefileCopy = src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig;',
    'if (dst->rc.zones && !preserveDstZones)',
    'x265_zone_free(dst);',
    'static bool ensureZoneCopyDestination(x265_param* dst, const x265_param* src, bool zonefileCopy)',
    'const int zoneAllocCount = zonefileCopy ? src->rc.zonefileCount : src->rc.zoneCount;',
    'dst->rc.zones = x265_zone_alloc(zoneAllocCount, zonefileCopy);',
    'if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))',
    'if (!src->rc.zones[i].zoneParam || !dst->rc.zones[i].zoneParam)',
    'x265_log(nullptr, X265_LOG_ERROR, "zonefile param copy requires non-null zoneParam storage\\n");',
    'dst->rc.zoneCount = src->rc.zoneCount;',
    'dst->rc.zonefileCount = src->rc.zonefileCount;',
)
FORBIDDEN_SNIPPETS = (
    'dst->rc.zoneCount = src->rc.zoneCount;\n    dst->rc.zonefileCount = src->rc.zonefileCount;\n    dst->reconfigWindowSize = src->reconfigWindowSize;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text and 'x265_zone_free(dst);' not in text[:text.find(snippet)]:
            failures.append((TARGET.as_posix(), 0, f'forbidden copy_params zone replacement regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing copy_params zone replacement guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
        brace_start = text.find('{', start)
        if brace_start == -1:
            return text[start:]
        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return text[start:]

    helper_text = extract_braced_block('static bool ensureZoneCopyDestination(x265_param* dst, const x265_param* src, bool zonefileCopy)')
    copy_text = extract_braced_block('void x265_copy_params(x265_param* dst, x265_param* src)')

    helper_count_pos = helper_text.find('const int zoneAllocCount = zonefileCopy ? src->rc.zonefileCount : src->rc.zoneCount;')
    helper_alloc_pos = helper_text.find('dst->rc.zones = x265_zone_alloc(zoneAllocCount, zonefileCopy);', helper_count_pos if helper_count_pos != -1 else 0)
    if -1 in (helper_count_pos, helper_alloc_pos) or not (helper_count_pos < helper_alloc_pos):
        failures.append((TARGET.as_posix(), 0, 'ensureZoneCopyDestination must derive zoneAllocCount before allocating zone storage'))

    free_pos = copy_text.find('if (dst->rc.zones && !preserveDstZones)')
    ensure_pos = copy_text.find('if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))')
    count_pos = copy_text.find('dst->rc.zoneCount = src->rc.zoneCount;')
    filecount_pos = copy_text.find('dst->rc.zonefileCount = src->rc.zonefileCount;')
    zone_guard_pos = copy_text.find('if (!src->rc.zones[i].zoneParam || !dst->rc.zones[i].zoneParam)', filecount_pos if filecount_pos != -1 else 0)
    if -1 not in (free_pos, ensure_pos, count_pos, filecount_pos) and not (free_pos < ensure_pos < count_pos < filecount_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_copy_params must release non-reused zone storage before overwriting zone counts'))
    if -1 in (ensure_pos, count_pos, filecount_pos, zone_guard_pos) or not (ensure_pos < count_pos < filecount_pos < zone_guard_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_copy_params must stage zone-count updates before zonefile param dereferences'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_copy_params zone replacement safety guardrails')
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

    print('x265_copy_params zone replacement safety validated')


if __name__ == '__main__':
    main()
