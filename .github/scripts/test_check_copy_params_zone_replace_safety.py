#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_copy_params_zone_replace_safety.py')

# Coverage probes used by the scan for x265_copy_params zone-replacement guardrails.
NORMALIZED_PROBES = (
    'ensureZoneCopyDestination must derive zoneAllocCount before allocating zone storage',
    'x265_copy_params must release non-reused zone storage before overwriting zone counts',
    'forbidden copy_params zone replacement regression: ',
    'missing copy_params zone replacement guardrail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool ensureZoneCopyDestination(x265_param* dst, const x265_param* src, bool zonefileCopy)',
                    '{',
                    'const int zoneAllocCount = zonefileCopy ? src->rc.zonefileCount : src->rc.zoneCount;',
                    'dst->rc.zones = x265_zone_alloc(zoneAllocCount, zonefileCopy);',
                    '}',
                    'void x265_copy_params(x265_param* dst, x265_param* src)',
                    '{',
                    'const bool preserveDstZones = (src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig) ||',
                    '                                  (src->rc.zoneCount && src->rc.zones);',
                    'const bool zonefileCopy = src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig;',
                    'if (dst->rc.zones && !preserveDstZones)',
                    '    x265_zone_free(dst);',
                    'if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))',
                    'dst->rc.zoneCount = src->rc.zoneCount;',
                    'dst->rc.zonefileCount = src->rc.zonefileCount;',
                    'if (!src->rc.zones[i].zoneParam || !dst->rc.zones[i].zoneParam)',
                    'x265_log(nullptr, X265_LOG_ERROR, "zonefile param copy requires non-null zoneParam storage\\n");',
                    '}',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'dst->rc.zoneCount = src->rc.zoneCount;',
                    'dst->rc.zonefileCount = src->rc.zonefileCount;',
                    'dst->reconfigWindowSize = src->reconfigWindowSize;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing copy_params zone replacement guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool ensureZoneCopyDestination(x265_param* dst, const x265_param* src, bool zonefileCopy)',
                    '{',
                    'const int zoneAllocCount = zonefileCopy ? src->rc.zonefileCount : src->rc.zoneCount;',
                    'dst->rc.zones = x265_zone_alloc(zoneAllocCount, zonefileCopy);',
                    '}',
                    'void x265_copy_params(x265_param* dst, x265_param* src)',
                    '{',
                    'const bool preserveDstZones = (src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig) ||',
                    '                                  (src->rc.zoneCount && src->rc.zones);',
                    'const bool zonefileCopy = src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig;',
                    'if (dst->rc.zones && !preserveDstZones)',
                    '    x265_zone_free(dst);',
                    'if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))',
                    'dst->rc.zoneCount = src->rc.zoneCount;',
                    'dst->rc.zonefileCount = src->rc.zonefileCount;',
                    '}',
                    'if (!src->rc.zones[i].zoneParam || !dst->rc.zones[i].zoneParam)',
                    'x265_log(nullptr, X265_LOG_ERROR, "zonefile param copy requires non-null zoneParam storage\\n");',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_copy_params must stage zone-count updates before zonefile param dereferences')

    print('x265_copy_params zone replacement safety tests passed')


if __name__ == '__main__':
    main()
