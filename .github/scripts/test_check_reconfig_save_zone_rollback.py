#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reconfig_save_zone_rollback.py')

# Coverage probes used by the scan for reconfig save-zone rollback guardrails.
NORMALIZED_PROBES = (
    'forbidden reconfig save zone rollback regression: ',
    'missing reconfig save zone rollback guardrail: ',
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
                    'static x265_zone* preserveNoResetZonefileZones(x265_param* dst, x265_param* src, int& zonefileCount)',
                    'static void restoreNoResetZonefileZones(x265_param* dst, x265_zone* zones, int zonefileCount)',
                    'int savedZonefileCount = 0;',
                    'x265_copy_params(&save, encoder->m_latestParam);',
                    'restoreNoResetZonefileZones(&save, preserveNoResetZonefileZones(&save, encoder->m_latestParam, savedZonefileCount), savedZonefileCount);',
                    'int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);',
                    'x265_copy_params(encoder->m_latestParam, &save);',
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
                    'x265_copy_params(&save, encoder->m_latestParam);',
                    'int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing reconfig save zone rollback guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'int savedZonefileCount = 0;',
                    'restoreNoResetZonefileZones(&save, preserveNoResetZonefileZones(&save, encoder->m_latestParam, savedZonefileCount), savedZonefileCount);',
                    'x265_copy_params(&save, encoder->m_latestParam);',
                    'int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);',
                    'x265_copy_params(encoder->m_latestParam, &save);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'reconfig save rollback order must remain copy -> restore no-reset zones -> reconfigure')

    print('Reconfig save zone rollback tests passed')


if __name__ == '__main__':
    main()
