#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reconplay_pipe_fail_state.py')


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
                'source/output/reconplay.cpp': '\n'.join((
                    'if (std::fprintf(outputPipe, "YUV4MPEG2 W%d H%d F%d:%d Ip C%s%s\\n", width, height, param.fpsNum, param.fpsDenom, csp, depth) < 0',
                    '    || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    bool closeFailed = std::ferror(outputPipe) != 0;',
                    '    if (pclose(outputPipe))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    '    outputPipe = nullptr;',
                    '    goto fail;',
                    '}',
                    'if (std::fprintf(outputPipe, "FRAME\\n") < 0 || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    pipeValid = false;',
                    '    return false;',
                    '}',
                    'if (retCount <= 0 || std::ferror(outputPipe) || !pipeValid)',
                    '{',
                    '    pipeValid = false;',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/reconplay.cpp': 'std::fprintf(outputPipe, "FRAME\\n");\n'})
        expect_fail(run_checker(root), 'missing ReconPlay pipe fail-state guardrail: if (std::fprintf(outputPipe, "YUV4MPEG2 W%d H%d F%d:%d Ip C%s%s\\n", width, height, param.fpsNum, param.fpsDenom, csp, depth) < 0')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'if (std::fprintf(outputPipe, "YUV4MPEG2 W%d H%d F%d:%d Ip C%s%s\\n", width, height, param.fpsNum, param.fpsDenom, csp, depth) < 0',
                    '    || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    bool closeFailed = std::ferror(outputPipe) != 0;',
                    '    if (pclose(outputPipe))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    '    outputPipe = nullptr;',
                    '    goto fail;',
                    '}',
                    'if (std::fprintf(outputPipe, "FRAME\\n") < 0 || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    pipeValid = false;',
                    '    return false;',
                    '}',
                    'if (retCount <= 0 || std::ferror(outputPipe) || !pipeValid)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ReconPlay pipe failures must lock pipeValid false in both frame-header and payload paths')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'if (std::fprintf(outputPipe, "YUV4MPEG2 W%d H%d F%d:%d Ip C%s%s\\n", width, height, param.fpsNum, param.fpsDenom, csp, depth) < 0',
                    '    || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    bool closeFailed = std::ferror(outputPipe) != 0;',
                    '    if (pclose(outputPipe))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    '    outputPipe = nullptr;',
                    '    goto fail;',
                    '}',
                    'if (std::fprintf(outputPipe, "FRAME\\n") < 0 || std::fflush(outputPipe) || std::ferror(outputPipe))',
                    '{',
                    '    pipeValid = false;',
                    '    return false;',
                    '}',
                    'if (retCount <= 0 || std::ferror(outputPipe) || !pipeValid)',
                    '{',
                    '    pipeValid = false;',
                    '    return false;',
                    '}',
                    'if (std::ferror(outputPipe) || pclose(outputPipe))',
                    '    pipeValid = false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ReconPlay short-circuit pclose regression')

    print('ReconPlay pipe fail-state guard tests passed')


if __name__ == '__main__':
    main()
