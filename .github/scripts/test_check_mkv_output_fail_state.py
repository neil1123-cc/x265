#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_mkv_output_fail_state.py')

# Coverage probes used by the scan for MKV output fail-state guardrails.
NORMALIZED_PROBES = (
    'MKV output must reject writes after fail-state or writer teardown in both header and frame paths',
    'MKV output must mark fail-state on all write/header error returns',
    'missing MKV output fail-state guardrail: ',
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
                'source/output/mkv.cpp': '\n'.join((
                    'if (b_fail || !p_mkv || !p_mkv->w)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (!p_mkv->width || !p_mkv->height ||',
                    '    !p_mkv->d_width || !p_mkv->d_height)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (mk_start_frame(p_mkv->w) < 0)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (mk_add_frame_data(p_mkv->w, p_nal[3].payload, p_nal[3].sizeBytes) < 0)',
                    '{',
                        '    b_fail = true;',
                        '    return -1;',
                    '}',
                    'if (b_fail || !p_mkv || !p_mkv->w)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (mk_add_frame_data(p_mkv->w, p_nalu[i].payload, p_nalu[i].sizeBytes) < 0)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'if (mk_set_frame_flags(p_mkv->w, i_stamp, b_keyframe, b_bframe) < 0)',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'b_fail = true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/mkv.cpp': 'if (mk_start_frame(p_mkv->w) < 0)\n{\n    return -1;\n}\n'})
        expect_fail(run_checker(root), 'missing MKV output fail-state guardrail')

    print('MKV output fail-state guard tests passed')


if __name__ == '__main__':
    main()
