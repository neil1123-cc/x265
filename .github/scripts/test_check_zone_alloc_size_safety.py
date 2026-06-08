#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zone_alloc_size_safety.py')

# Coverage probes used by the scan for x265_zone_alloc size guardrails.
NORMALIZED_PROBES = (
    'forbidden zone alloc size regression: if ((size_t)zoneCount >= SIZE_MAX / sizeof(x265_zone))',
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
                    'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
                    '{',
                    '    if (zoneCount <= 0)',
                    '        return nullptr;',
                    '    if ((size_t)zoneCount > SIZE_MAX / sizeof(x265_zone))',
                    '        return nullptr;',
                    '    x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
                    '    if (!zone)',
                    '        return nullptr;',
                    '    std::fill_n(zone, zoneCount, x265_zone());',
                    '    if (isZoneFile)',
                    '    {',
                    '        for (int i = 0; i < zoneCount; i++)',
                    '        {',
                    '            zone[i].zoneParam = x265_param_alloc();',
                    '            if (!zone[i].zoneParam)',
                    '            {',
                    '                for (int j = 0; j < i; j++)',
                    '                    PARAM_NS::x265_param_free(zone[j].zoneParam);',
                    '                x265_free(zone);',
                    '                return nullptr;',
                    '            }',
                    '        }',
                    '    }',
                    '    return zone;',
                    '}',
                    'void x265_zone_free(x265_param *param)',
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
                    'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
                    '{',
                    '    if (zoneCount <= 0)',
                    '        return nullptr;',
                    '    if ((size_t)zoneCount >= SIZE_MAX / sizeof(x265_zone))',
                    '        return nullptr;',
                    '    x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zone alloc size regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
                    '{',
                    '    if (zoneCount <= 0)',
                    '        return nullptr;',
                    '    x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing zone alloc size guardrail: if ((size_t)zoneCount > SIZE_MAX / sizeof(x265_zone))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'x265_zone *x265_zone_alloc(int zoneCount, int isZoneFile)',
                    '{',
                    '    x265_zone* zone = (x265_zone*)x265_malloc(sizeof(x265_zone) * zoneCount);',
                    '    if (zoneCount <= 0)',
                    '        return nullptr;',
                    '    if ((size_t)zoneCount > SIZE_MAX / sizeof(x265_zone))',
                    '        return nullptr;',
                    '    if (!zone)',
                    '        return nullptr;',
                    '    std::fill_n(zone, zoneCount, x265_zone());',
                    '    if (isZoneFile)',
                    '    {',
                    '        for (int i = 0; i < zoneCount; i++)',
                    '        {',
                    '            zone[i].zoneParam = x265_param_alloc();',
                    '            if (!zone[i].zoneParam)',
                    '            {',
                    '                x265_free(zone);',
                    '                for (int j = 0; j < i; j++)',
                    '                    PARAM_NS::x265_param_free(zone[j].zoneParam);',
                    '                return nullptr;',
                    '            }',
                    '        }',
                    '    }',
                    '    return zone;',
                    '}',
                    'void x265_zone_free(x265_param *param)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_zone_alloc must preserve the reviewed size guards and zoneParam rollback ordering before returning an allocated zone array')

    print('Zone alloc size safety tests passed')


if __name__ == '__main__':
    main()
