#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ip_pb_ratio_parse_safety.py')


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


PASS_SOURCE = '\n'.join((
    'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
    'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
    'OPT("hevc-aq")',
    'CHECK(param->rc.ipFactor <= 0,',
    '    "ipratio must be greater than 0");',
    'CHECK(param->rc.pbFactor <= 0,',
    '    "pbratio must be greater than 0");',
    'CHECK(param->rc.aqBiasStrength < 0 || param->rc.aqBiasStrength > 3,',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("ipratio") p->rc.ipFactor = atof(value);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ip/pb ratio regression: OPT("ipratio") p->rc.ipFactor = atof(value);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
                    'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
                    'CHECK(param->rc.ipFactor <= 0,',
                    '    "ipratio must be greater than 0");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ip/pb ratio guardrail: CHECK(param->rc.pbFactor <= 0,')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
                    'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
                    'OPT("hevc-aq")',
                    'CHECK(param->rc.pbFactor <= 0,',
                    '    "pbratio must be greater than 0");',
                    'CHECK(param->rc.ipFactor <= 0,',
                    '    "ipratio must be greater than 0");',
                    'CHECK(param->rc.aqBiasStrength < 0 || param->rc.aqBiasStrength > 3,',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ipratio/pbratio parsing must preserve the reviewed ipratio-before-pbratio parse order')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'CHECK(param->rc.ipFactor <= 0,\n'
                    '    "ipratio must be greater than 0");\n'
                    'CHECK(param->rc.pbFactor <= 0,\n'
                    '    "pbratio must be greater than 0");\n',
                    'CHECK(param->rc.pbFactor <= 0,\n'
                    '    "pbratio must be greater than 0");\n'
                    'CHECK(param->rc.ipFactor <= 0,\n'
                    '    "ipratio must be greater than 0");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'ipratio/pbratio validation must keep the reviewed ipratio-before-pbratio range checks')

    print('IP/PB ratio parse safety tests passed')


if __name__ == '__main__':
    main()
