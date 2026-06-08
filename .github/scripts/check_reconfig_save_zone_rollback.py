#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'static x265_zone* preserveNoResetZonefileZones(x265_param* dst, x265_param* src, int& zonefileCount)',
    'static void restoreNoResetZonefileZones(x265_param* dst, x265_zone* zones, int zonefileCount)',
    'int savedZonefileCount = 0;',
    'x265_copy_params(&save, encoder->m_latestParam);',
    'restoreNoResetZonefileZones(&save, preserveNoResetZonefileZones(&save, encoder->m_latestParam, savedZonefileCount), savedZonefileCount);',
    'x265_copy_params(encoder->m_latestParam, &save);',
)
FORBIDDEN_SNIPPETS = (
    'x265_copy_params(&save, encoder->m_latestParam);\n    int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden reconfig save zone rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing reconfig save zone rollback guardrail: {snippet}'))

    copy_pos = text.find('x265_copy_params(&save, encoder->m_latestParam);')
    restore_pos = text.find('restoreNoResetZonefileZones(&save, preserveNoResetZonefileZones(&save, encoder->m_latestParam, savedZonefileCount), savedZonefileCount);')
    ret_pos = text.find('int ret = encoder->reconfigureParam(encoder->m_latestParam, param_in);')
    if -1 not in (copy_pos, restore_pos, ret_pos) and not (copy_pos < restore_pos < ret_pos):
        failures.append((TARGET.as_posix(), 0, 'reconfig save rollback order must remain copy -> restore no-reset zones -> reconfigure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reconfig save zone rollback guardrails')
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

    print('Reconfig save zone rollback validated')


if __name__ == '__main__':
    main()
