#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zone_parse_replace_safety.py')

# Coverage probes used by the scan for zone parse-replacement guardrails.
NORMALIZED_PROBES = (
    'zone parse replacement must clear old zone state before assigning the new one',
    'missing zone parse replacement guardrail: if (!bZoneParseError)',
    """forbidden zone parse replacement regression: if (!bZoneParseError)
        {
            p->rc.zoneCount = zoneCount;
            p->rc.zones = zones;
        }""",
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
                    'if (!bZoneParseError)',
                    '{',
                    '    x265_zone_free(p);',
                    '    p->rc.zoneCount = zoneCount;',
                    '    p->rc.zones = zones;',
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
                    'if (!bZoneParseError)',
                    '{',
                    '    p->rc.zoneCount = zoneCount;',
                    '    p->rc.zones = zones;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing zone parse replacement guardrail')

    print('Zone parse replacement safety tests passed')


if __name__ == '__main__':
    main()
