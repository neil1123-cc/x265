#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_reconplay_pclose_state.py')


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
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    'ReconPlay::~ReconPlay()',
                    '{',
                    '    pipeValid = false;',
                    '    if (outputPipe)',
                    '    {',
                    '        bool closeFailed = std::ferror(outputPipe) != 0;',
                    '        if (pclose(outputPipe))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
                    '    }',
                    '    outputPipe = nullptr;',
                    '}',
                    '    general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/reconplay.cpp': 'pclose(outputPipe);\n'})
        expect_fail(run_checker(root), 'missing reconplay pclose guardrail: bool closeFailed = std::ferror(outputPipe) != 0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    'if (std::ferror(outputPipe) || pclose(outputPipe))',
                    '    general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden reconplay short-circuit pclose regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(outputPipe) != 0;',
                    'if (pclose(outputPipe))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    general_log(&param, "exec", X265_LOG_WARNING, "Unable to close recon playback pipe after header failure\\n");',
                    'pipeValid = false;',
                    'outputPipe = nullptr;',
                    'general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ReconPlay destructor')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/reconplay.cpp': '\n'.join((
                    'ReconPlay::~ReconPlay()',
                    '{',
                    '    if (outputPipe)',
                    '    {',
                    '        bool closeFailed = std::ferror(outputPipe) != 0;',
                    '        if (pclose(outputPipe))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            general_log(nullptr, "exec", X265_LOG_WARNING, "Unable to finalize recon playback pipe state\\n");',
                    '    }',
                    '    outputPipe = nullptr;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ReconPlay destructor must clear pipeValid and outputPipe when finalizing the pipe')

    print('Reconplay pclose guard tests passed')


if __name__ == '__main__':
    main()
