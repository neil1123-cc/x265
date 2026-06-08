#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vbv_fullness_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing vbv-fullness guardrail: ',
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
                    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
                    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
                    'OPT("video-signal-type-preset")',
                    'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,',
                    '    "min-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
                    '    "max-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->rc.bitrate < 0,',
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
                    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
                    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
                    'CHECK(param->minVbvFullness < 0 && param->minVbvFullness > 100,',
                    '    "min-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
                    '    "max-vbv-fullness must be a fraction 0 - 100");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden vbv-fullness regression: CHECK(param->minVbvFullness < 0 && param->minVbvFullness > 100,')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join(((
                    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
                    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
                    'OPT("video-signal-type-preset")',
                    'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
                    '    "max-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,',
                    '    "min-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->rc.bitrate < 0,',
                ))) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VBV fullness parsing must preserve the reviewed min-before-max parse order')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join(((
                    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
                    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
                    'OPT("video-signal-type-preset")',
                    'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
                    '    "max-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,',
                    '    "min-vbv-fullness must be a fraction 0 - 100");',
                    'CHECK(param->rc.bitrate < 0,',
                ))) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VBV fullness validation must preserve the reviewed min-before-max range check order')

    print('VBV fullness parse safety tests passed')


if __name__ == '__main__':
    main()
