#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zimg_init_rollback.py')

# Coverage probes used by the scan for ZIMG init rollback guardrails.
NORMALIZED_PROBES = (
    'missing ZIMG init rollback guardrail: ',
    'forbidden ZIMG init rollback regression: ',
    'ZIMG init must release stale graph state before deriving new resize buffer geometry',
    'ZIMG init must preserve both resize-buffer geometry guardrails',
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
                'source/filters/zimgfilter.cpp': '\n'.join((
                    'void ZimgFilter::release()',
                    'void ZimgFilter::processFrame(x265_picture& picture)',
                    '{',
                    'if (!graph) // Init',
                    '{',
                    'release();',
                    'int pixelSize = OutputDepth > 8 ? 2 : 1;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane geometry\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'zimg_get_last_error(fail_str, sizeof(fail_str));',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for temp buffer\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    '}',
                    'zimg_image_buffer_const src_buf = {}',
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
                'source/filters/zimgfilter.cpp': 'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");\n            bFail = true;\n            return;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ZIMG init rollback regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/filters/zimgfilter.cpp': '\n'.join((
                    'void ZimgFilter::release()',
                    'void ZimgFilter::processFrame(x265_picture& picture)',
                    '{',
                    'if (!graph) // Init',
                    '{',
                    'release();',
                    'int pixelSize = OutputDepth > 8 ? 2 : 1;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");',
                    'bFail = true;',
                    'release();',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane geometry\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'zimg_get_last_error(fail_str, sizeof(fail_str));',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\\n", fail_str);',
                    'release();',
                    'bFail = true;',
                    'return;',
                    'general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for temp buffer\\n");',
                    'release();',
                    'bFail = true;',
                    'return;',
                    '}',
                    'zimg_image_buffer_const src_buf = {}',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ZIMG init must release stale state after the first invalid resize-buffer geometry failure')

    print('ZIMG init rollback tests passed')


if __name__ == '__main__':
    main()
