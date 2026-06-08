#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_query_api_output_null_guards.py')


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
        'int x265_get_slicetype_poc_and_scenecut(x265_encoder *enc, int *slicetype, int *poc, int *sceneCut)',
        '{',
        '    if (!enc || !slicetype || !poc || !sceneCut)',
        '        return -1;',
        '    if (!encoder->copySlicetypePocAndSceneCut(slicetype, poc, sceneCut, 0))',
        '        return 0;',
        '    return -1;',
        '}',
        'int x265_get_ref_frame_list(x265_encoder *enc, x265_picyuv** l0, x265_picyuv** l1, int sliceType, int poc, int* pocL0, int* pocL1)',
        '{',
        '    if (!enc || !l0 || !l1 || !pocL0 || !pocL1)',
        '        return -1;',
        '    return encoder->getRefFrameList((PicYuv**)l0, (PicYuv**)l1, sliceType, poc, pocL0, pocL1);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!enc || !slicetype || !poc || !sceneCut)\n        return -1;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_get_slicetype_poc_and_scenecut output null guardrail: if (!enc || !slicetype || !poc || !sceneCut)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!enc || !l0 || !l1 || !pocL0 || !pocL1)\n        return -1;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_get_ref_frame_list output null guardrail: if (!enc || !l0 || !l1 || !pocL0 || !pocL1)')

    print('Query API output null guard tests passed')


if __name__ == '__main__':
    main()
