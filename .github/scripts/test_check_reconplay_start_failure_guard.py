#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reconplay_start_failure_guard.py')


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
                    'pipeValid = true;',
                    'threadActive.store(true);',
                    'if (start())',
                    '    return;',
                    'general_log(&param, "exec", X265_LOG_ERROR, "Unable to start recon playback thread\\n");',
                    'threadActive.store(false);',
                    'pipeValid = false;',
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after thread start failure\\n");',
                    'outputPipe = nullptr;',
                    'goto fail;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': 'pipeValid = true;\nthreadActive.store(true);\nstart();\nreturn;\n',
            },
        )
        expect_fail(run_checker(root), 'missing reconplay start failure guardrail: if (start())')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'pipeValid = true;',
                    'threadActive.store(true);',
                    'if (start())',
                    '    return;',
                    'general_log(&param, "exec", X265_LOG_ERROR, "Unable to start recon playback thread\\n");',
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after thread start failure\\n");',
                    'threadActive.store(false);',
                    'pipeValid = false;',
                    'outputPipe = nullptr;',
                    'goto fail;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ReconPlay constructor must reset thread state and close the pipe when thread startup fails')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'pipeValid = true;',
                    'threadActive.store(true);',
                    'if (start())',
                    '    return;',
                    'general_log(&param, "exec", X265_LOG_ERROR, "Unable to start recon playback thread\\n");',
                    'threadActive.store(false);',
                    'pipeValid = false;',
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after thread start failure\\n");',
                    'outputPipe = nullptr;',
                    'goto fail;',
                    'if (std::ferror(outputPipe) || pclose(outputPipe))',
                    '    outputPipe = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden reconplay thread-start short-circuit pclose regression')

    print('Reconplay start failure guard tests passed')


if __name__ == '__main__':
    main()
