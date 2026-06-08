#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_x265_main_cleanup_state.py')


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
                'source/x265.cpp': '\n'.join((
                    'int main(int argc, char **argv)',
                    '{',
                    '    int ret = 0;',
                    '    CLIOptions* cliopt = nullptr;',
                    '    AbrEncoder* abrEnc = nullptr;',
                    '    ret = 1;',
                    '    else if (cliopt[0].parseExitCode >= 0)',
                    '        ret = cliopt[0].parseExitCode;',
                    '    goto cleanup;',
                    'cleanup:',
                    '    if (abrConfig)',
                    '    {',
                    '        bool closeFailed = std::ferror(abrConfig) != 0;',
                    '        if (std::fclose(abrConfig))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\\n");',
                    '        abrConfig = nullptr;',
                    '    }',
                    '    if (abrEnc)',
                    '    {',
                    '        abrEnc->destroy();',
                    '        delete abrEnc;',
                    '    }',
                    '    bool destroyFailed = false;',
                    '    if (cliopt)',
                    '        destroyFailed |= cliopt[idx].destroy();',
                    '    if (!ret && destroyFailed)',
                    '        ret = 3;',
                    '    delete[] cliopt;',
                    '    return ret;',
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
                'source/x265.cpp': 'if (isAbrLadder && !abrConfig)\n        std::exit(1);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden x265 main cleanup regression: if (isAbrLadder && !abrConfig)\n        std::exit(1);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': 'int ret = 0;\ncleanup:\n',
            },
        )
        expect_fail(run_checker(root), 'missing x265 main cleanup guardrail: CLIOptions* cliopt = nullptr;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': '\n'.join((
                    'int ret = 0;',
                    'CLIOptions* cliopt = nullptr;',
                    'AbrEncoder* abrEnc = nullptr;',
                    'ret = 1;',
                    'else if (cliopt[0].parseExitCode >= 0)',
                    'ret = cliopt[0].parseExitCode;',
                    'goto cleanup;',
                    'cleanup:',
                    'if (abrConfig)',
                    'bool closeFailed = std::ferror(abrConfig) != 0;',
                    'if (std::fclose(abrConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\\n");',
                    'abrConfig = nullptr;',
                    'if (abrEnc)',
                    '    abrEnc->destroy();',
                    '    delete abrEnc;',
                    'bool destroyFailed = false;',
                    'if (cliopt)',
                    '    destroyFailed |= cliopt[idx].destroy();',
                    'if (!ret && destroyFailed)',
                    '    ret = 3;',
                    'delete[] cliopt;',
                    'if (std::ferror(abrConfig) || std::fclose(abrConfig))',
                    '    ret = 1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden x265 main cleanup regression: std::ferror(abrConfig) || std::fclose(abrConfig)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': '\n'.join((
                    'int main(int argc, char **argv)',
                    '{',
                    '    int ret = 0;',
                    '    CLIOptions* cliopt = nullptr;',
                    '    AbrEncoder* abrEnc = nullptr;',
                    '    ret = 1;',
                    '    else if (cliopt[0].parseExitCode >= 0)',
                    '        ret = cliopt[0].parseExitCode;',
                    '    goto cleanup;',
                    'cleanup:',
                    '    if (abrEnc)',
                    '    {',
                    '        abrEnc->destroy();',
                    '        delete abrEnc;',
                    '    }',
                    '    if (abrConfig)',
                    '    {',
                    '        bool closeFailed = std::ferror(abrConfig) != 0;',
                    '        if (std::fclose(abrConfig))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\\n");',
                    '        abrConfig = nullptr;',
                    '    }',
                    '    bool destroyFailed = false;',
                    '    if (cliopt)',
                    '        destroyFailed |= cliopt[idx].destroy();',
                    '    if (!ret && destroyFailed)',
                    '        ret = 3;',
                    '    delete[] cliopt;',
                    '    return ret;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265 main cleanup must finalize abrConfig before tearing down the encoder and CLI options')

    print('x265 main cleanup guard tests passed')


if __name__ == '__main__':
    main()
