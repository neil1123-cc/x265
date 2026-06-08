#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_param_storage_replace_safety.py')

# Coverage probes used by the scan for SVT parameter-storage replacement guardrails.
NORMALIZED_PROBES = (
    'forbidden SVT param storage regression: ',
    'missing SVT param storage guardrail: ',
    'SVT zone param storage must be staged before overwrite and validated after finalizeZoneParamCopy',
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
                    'void* zoneSvtHevcParam = param->rc.zones[i].zoneParam->svtHevcParam;',
                    'memcpy(param->rc.zones[i].zoneParam, param, sizeof(x265_param));',
                    'param->rc.zones[i].zoneParam->svtHevcParam = zoneSvtHevcParam;',
                    'finalizeZoneParamCopy(param->rc.zones[i].zoneParam, param);',
                    'if (param->svtHevcParam && !param->rc.zones[i].zoneParam->svtHevcParam)',
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
                    'dst->svtHevcParam = x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));',
                    'if (!dst->svtHevcParam)',
                    'memcpy(dst->svtHevcParam, src->svtHevcParam, sizeof(EB_H265_ENC_CONFIGURATION));',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT param storage regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'memcpy(param->rc.zones[i].zoneParam, param, sizeof(x265_param));',
                    'void* zoneSvtHevcParam = param->rc.zones[i].zoneParam->svtHevcParam;',
                    'param->rc.zones[i].zoneParam->svtHevcParam = zoneSvtHevcParam;',
                    'finalizeZoneParamCopy(param->rc.zones[i].zoneParam, param);',
                    'if (param->svtHevcParam && !param->rc.zones[i].zoneParam->svtHevcParam)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT zone param storage must be staged before overwrite')

    print('SVT param storage replace safety tests passed')


if __name__ == '__main__':
    main()
