#!/usr/bin/env python3
import argparse
from pathlib import Path


PARAM_TARGET = Path('source/common/param.cpp')
API_TARGET = Path('source/encoder/api.cpp')
PARAM_REQUIRED_SNIPPETS = (
    'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
    '"Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
)
API_REQUIRED_SNIPPETS = (
    'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
    'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
    'if (activeParam->reconfigWindowSize)',
    'memcpy(zone->relativeComplexity, zone_in->relativeComplexity, sizeof(double) * activeParam->reconfigWindowSize);',
    'return -1;',
)
FORBIDDEN_SNIPPETS = (
    'CHECK(param->reconfigWindowSize >= SIZE_MAX / sizeof(double),',
    'if (activeParam->reconfigWindowSize >= SIZE_MAX / sizeof(double))',
    'CHECK(param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
    'if (activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
)
def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    param_path = repo_root / PARAM_TARGET
    api_path = repo_root / API_TARGET
    if not param_path.is_file():
        return [(PARAM_TARGET.as_posix(), 0, 'missing file')]
    if not api_path.is_file():
        return [(API_TARGET.as_posix(), 0, 'missing file')]

    param_text = param_path.read_text(encoding='utf-8', errors='ignore')
    api_text = api_path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in param_text or snippet in api_text:
            failures.append((PARAM_TARGET.as_posix(), 0, f'forbidden reconfig window size regression: {snippet}'))
            return failures
    for snippet in PARAM_REQUIRED_SNIPPETS:
        if snippet not in param_text:
            failures.append((PARAM_TARGET.as_posix(), 0, f'missing reconfig window size guardrail: {snippet}'))
    for snippet in API_REQUIRED_SNIPPETS:
        if snippet not in api_text:
            failures.append((API_TARGET.as_posix(), 0, f'missing reconfig window size guardrail: {snippet}'))
    if all(snippet in param_text for snippet in PARAM_REQUIRED_SNIPPETS):
        if not has_in_order(
            param_text,
            (
                'CHECK(param->rc.zonefileCount && !param->bResetZoneConfig && !param->reconfigWindowSize,',
                '"Zonefile reconfiguration without RC reset requires a non-zero reconfig window size");',
                'CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),',
                '"Zonefile reconfiguration window size exceeds supported relativeComplexity storage");',
            ),
        ):
            failures.append((PARAM_TARGET.as_posix(), 0, 'reconfigWindowSize validation must keep the zero-size precondition ahead of the relativeComplexity overflow guard'))
    if all(snippet in api_text for snippet in API_REQUIRED_SNIPPETS):
        if not has_in_order(
            api_text,
            (
                'if ((size_t)activeParam->reconfigWindowSize > SIZE_MAX / sizeof(double))',
                'x265_log(activeParam, X265_LOG_ERROR, "Zone reconfiguration window size exceeds supported relativeComplexity storage\\n");',
                'return -1;',
                'if (activeParam->reconfigWindowSize)',
                'memcpy(zone->relativeComplexity, zone_in->relativeComplexity, sizeof(double) * activeParam->reconfigWindowSize);',
            ),
        ):
            failures.append((API_TARGET.as_posix(), 0, 'Zone reconfiguration must preserve the reviewed overflow guard before any relativeComplexity memcpy'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reconfigWindowSize safety guardrails')
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

    print('Reconfig window size safety validated')


if __name__ == '__main__':
    main()
