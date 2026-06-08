#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zone_and_scenecut_param_parse_null_guards.py')

# Coverage probes used by the scan for zone/scenecut param-parse null guardrails.
NORMALIZED_PROBES = (
    'missing  parser',
    'missing  null guardrail: ',
    'missing x265_scenecut_aware_qp_param_parse parser',
    'missing x265_zone_param_parse parser',
    """missing x265_scenecut_aware_qp_param_parse null guardrail: if (!name)
        return X265_PARAM_BAD_NAME;""",
    """missing x265_scenecut_aware_qp_param_parse null guardrail: if (!p)
        return X265_PARAM_BAD_VALUE;""",
    'missing x265_scenecut_aware_qp_param_parse null guardrail: p->bEnableSceneCutAwareQp = sceneCutAwareQp;',
    'x265_scenecut_aware_qp_param_parse must reject null p after validating name and before dereferencing parser state',
    """missing x265_zone_param_parse null guardrail: if (!name)
        return X265_PARAM_BAD_NAME;""",
    """missing x265_zone_param_parse null guardrail: if (!p)
        return X265_PARAM_BAD_VALUE;""",
    'missing x265_zone_param_parse null guardrail: p->maxNumReferences = maxNumReferences;',
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
        'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
        '{',
        '    if (!name)',
        '        return X265_PARAM_BAD_NAME;',
        '    if (!p)',
        '        return X265_PARAM_BAD_VALUE;',
        '    p->bEnableSceneCutAwareQp = sceneCutAwareQp;',
        '}',
        'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
        '{',
        '    if (!name)',
        '        return X265_PARAM_BAD_NAME;',
        '    if (!p)',
        '        return X265_PARAM_BAD_VALUE;',
        '    p->maxNumReferences = maxNumReferences;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    '    if (!p)\n        return X265_PARAM_BAD_VALUE;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_scenecut_aware_qp_param_parse null guardrail: if (!p)\n        return X265_PARAM_BAD_VALUE;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': valid_text().replace(
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)\n{\n    if (!name)\n        return X265_PARAM_BAD_NAME;\n    if (!p)\n        return X265_PARAM_BAD_VALUE;\n',
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)\n{\n    if (!p)\n        return X265_PARAM_BAD_VALUE;\n    if (!name)\n        return X265_PARAM_BAD_NAME;\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'x265_zone_param_parse must reject null p after validating name and before dereferencing parser state')

    print('x265 zone/scenecut param parse null guard tests passed')


if __name__ == '__main__':
    main()
