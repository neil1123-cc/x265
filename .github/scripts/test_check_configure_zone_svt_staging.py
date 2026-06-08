#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_configure_zone_svt_staging.py')

# Coverage probes used by the scan for configureZone SVT staging guardrails.
NORMALIZED_PROBES = (
    'configureZone must stage SVT storage before overwriting the zone object',
    'forbidden configureZone SVT staging regression: ',
    'missing configureZone SVT staging guardrail: ',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'void* stagedZoneSvtHevcParam = zoneSvtHevcParam;',
                    'if (p->svtHevcParam)',
                    '{',
                    '    if (!stagedZoneSvtHevcParam)',
                    '        stagedZoneSvtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    '    std::memcpy(stagedZoneSvtHevcParam, p->svtHevcParam, sizeof(EB_H265_ENC_CONFIGURATION));',
                    '}',
                    'else if (stagedZoneSvtHevcParam)',
                    '{',
                    '    x265_free(stagedZoneSvtHevcParam);',
                    '    stagedZoneSvtHevcParam = nullptr;',
                    '}',
                    'std::memcpy(zone, p, sizeof(x265_param));',
                    'zone->svtHevcParam = stagedZoneSvtHevcParam;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'std::memcpy(zone, p, sizeof(x265_param));',
                    'zone->svtHevcParam = zoneSvtHevcParam;',
                    'if (p->svtHevcParam)',
                    '{',
                    '    zoneSvtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing configureZone SVT staging guardrail')

    print('configureZone SVT staging tests passed')


if __name__ == '__main__':
    main()
