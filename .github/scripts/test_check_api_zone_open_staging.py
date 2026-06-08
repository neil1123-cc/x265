#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_api_zone_open_staging.py')

# Coverage probes used by the scan for API zone-open staging guardrails.
NORMALIZED_PROBES = (
    'forbidden zone open staging regression: ',
    'missing zone open staging guardrail: ',
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
                'source/encoder/api.cpp': '\n'.join((
                    'if (zoneAllocCount && (!p->rc.zonefileCount || p->bResetZoneConfig))',
                    '{',
                    '    param->rc.zoneCount = zoneAllocIsZoneFile ? 0 : p->rc.zoneCount;',
                    '}',
                    'x265_copy_params(param, p);',
                    'if (!param->bResetZoneConfig && param->rc.zonefileCount)',
                    '{',
                    '    param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
                    '    void* zoneSvtHevcParam = param->rc.zones[i].zoneParam->svtHevcParam;',
                    '    param->rc.zones[i].zoneParam->svtHevcParam = zoneSvtHevcParam;',
                    '    finalizeZoneParamCopy(param->rc.zones[i].zoneParam, param);',
                    '    if (param->svtHevcParam && !param->rc.zones[i].zoneParam->svtHevcParam)',
                    '        goto fail;',
                    '    param->rc.zones[i].startFrame = -1;',
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
                'source/encoder/api.cpp': '\n'.join((
                    'if (zoneAllocCount)',
                    '{',
                    '    param->rc.zoneCount = zoneAllocIsZoneFile ? 0 : p->rc.zoneCount;',
                    '}',
                    'x265_copy_params(param, p);',
                    'if (!param->bResetZoneConfig && param->rc.zonefileCount)',
                    '{',
                    '    param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing zone open staging guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'if (zoneAllocCount && (!p->rc.zonefileCount || p->bResetZoneConfig))',
                    '{',
                    '    param->rc.zoneCount = zoneAllocIsZoneFile ? 0 : p->rc.zoneCount;',
                    '}',
                    'if (!param->bResetZoneConfig && param->rc.zonefileCount)',
                    '{',
                    '    param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
                    '}',
                    'x265_copy_params(param, p);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'zone open staging order must remain copy -> no-reset branch -> zone allocation')

    print('Zone open staging tests passed')


if __name__ == '__main__':
    main()
