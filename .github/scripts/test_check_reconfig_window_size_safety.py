#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reconfig_window_size_safety.py')

# Coverage probes used by the scan for reconfig window-size guardrails.
NORMALIZED_PROBES = (
    'forbidden reconfig window size regression: ',
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
                    'CHECK(param->rc.zonefileCount && !param->bResetZoneConfig && !param->reconfigWindowSize,',
                    '      "Zonefile reconfiguration without RC reset requires a non-zero reconfig window size");',
                    'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
                    '      "Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
                    'if (param->rc.zonefileCount && param->rc.zones)',
                )) + '\n',
                'source/encoder/api.cpp': '\n'.join((
                    'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
                    '{',
                    '    x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
                    '    return -1;',
                    '}',
                    'if (activeParam->reconfigWindowSize)',
                    '    memcpy(zone->relativeComplexity, zone_in->relativeComplexity, sizeof(double) * activeParam->reconfigWindowSize);',
                    'encoder->zoneWriteCount[encoder->m_zoneIndex].incr();',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'CHECK(param->reconfigWindowSize >= SIZE_MAX / sizeof(double),\n',
                'source/encoder/api.cpp': 'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden reconfig window size regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
                    '      "Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
                )) + '\n',
                'source/encoder/api.cpp': '\n'.join((
                    'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
                    '{',
                    '    x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
                    '    return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing reconfig window size guardrail: if (activeParam->reconfigWindowSize)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
                    '      "Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
                    'CHECK(param->rc.zonefileCount && !param->bResetZoneConfig && !param->reconfigWindowSize,',
                    '      "Zonefile reconfiguration without RC reset requires a non-zero reconfig window size");',
                    'if (param->rc.zonefileCount && param->rc.zones)',
                )) + '\n',
                'source/encoder/api.cpp': '\n'.join((
                    'if (activeParam->reconfigWindowSize)',
                    '    memcpy(zone->relativeComplexity, zone_in->relativeComplexity, sizeof(double) * activeParam->reconfigWindowSize);',
                    'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
                    '{',
                    '    x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
                    '    return -1;',
                    '}',
                    'encoder->zoneWriteCount[encoder->m_zoneIndex].incr();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'reconfigWindowSize validation must keep the zero-size precondition ahead of the relativeComplexity overflow guard')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'CHECK(param->rc.zonefileCount && !param->bResetZoneConfig && !param->reconfigWindowSize,',
                    '      "Zonefile reconfiguration without RC reset requires a non-zero reconfig window size");',
                    'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
                    '      "Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
                    'if (param->rc.zonefileCount && param->rc.zones)',
                )) + '\n',
                'source/encoder/api.cpp': '\n'.join((
                    'if (activeParam->reconfigWindowSize)',
                    '    memcpy(zone->relativeComplexity, zone_in->relativeComplexity, sizeof(double) * activeParam->reconfigWindowSize);',
                    'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
                    '{',
                    '    x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
                    '    return -1;',
                    '}',
                    'encoder->zoneWriteCount[encoder->m_zoneIndex].incr();',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Zone reconfiguration must preserve the reviewed overflow guard before any relativeComplexity memcpy')

    print('Reconfig window size safety tests passed')


if __name__ == '__main__':
    main()
