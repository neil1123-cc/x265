#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_param_apply_profile_null_guard.py')

# Coverage probes used by the scan for x265_param_apply_profile null-guard checks.
NORMALIZED_PROBES = (
    'x265_param_apply_profile must reject null param before handling optional profile no-op or SVT/profile logic',
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


def valid_text():
    return '\n'.join((
        'int x265_param_apply_profile(x265_param *param, const char *profile)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_profile requires a non-null parameter struct\\n");',
        '        return -1;',
        '    }',
        '    if (!profile)',
        '        return 0;',
        '#ifdef SVT_HEVC',
        '    if (param->bEnableSvtHevc)',
        '        return 0;',
        '#endif',
        '    return 0;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/level.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/level.cpp': valid_text().replace(
                    '    if (!param)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_profile requires a non-null parameter struct\\n");\n'
                    '        return -1;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(
            run_checker(root),
            'missing x265_param_apply_profile null guardrail: if (!param)',
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/level.cpp': '\n'.join((
                    'int x265_param_apply_profile(x265_param *param, const char *profile)',
                    '{',
                    '    if (!param || !profile)',
                    '        return 0;',
                    '#ifdef SVT_HEVC',
                    '    return 0;',
                    '#endif',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(
            run_checker(root),
            'x265_param_apply_profile must not treat null param and null profile as the same success path',
        )

    print('x265_param_apply_profile null guard tests passed')


if __name__ == '__main__':
    main()
