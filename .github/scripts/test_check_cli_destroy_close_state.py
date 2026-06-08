#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_destroy_close_state.py')


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
                'source/x265cli.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'bool fileCloseFailed = std::ferror(qpfile) != 0;',
                    'if (std::fclose(qpfile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(zoneFile) != 0;',
                    'if (std::fclose(zoneFile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(dolbyVisionRpu) != 0;',
                    'if (std::fclose(dolbyVisionRpu))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(scenecutAwareQpConfig) != 0;',
                    'if (std::fclose(scenecutAwareQpConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'scenecutAwareQpConfig = nullptr;',
                    'bool fileCloseFailed = std::ferror(multiViewConfig) != 0;',
                    'if (std::fclose(multiViewConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'multiViewConfig = nullptr;',
                    'output->closeFile(0, 0);',
                    'output->release();',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");',
                    'if (param && api)',
                    '    api->param_free(param);',
                    'param = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': 'std::fclose(qpfile);\n'})
        expect_fail(run_checker(root), 'missing CLI destroy close-state guardrail: bool closeFailed = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'bool fileCloseFailed = std::ferror(qpfile) != 0;',
                    'if (std::fclose(qpfile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(zoneFile) != 0;',
                    'if (std::fclose(zoneFile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(dolbyVisionRpu) != 0;',
                    'if (std::fclose(dolbyVisionRpu))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(scenecutAwareQpConfig) != 0;',
                    'if (std::fclose(scenecutAwareQpConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'scenecutAwareQpConfig = nullptr;',
                    'bool fileCloseFailed = std::ferror(multiViewConfig) != 0;',
                    'if (std::fclose(multiViewConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'multiViewConfig = nullptr;',
                    'output->closeFile(0, 0);',
                    'output->release();',
                    'if (param && api)',
                    '    api->param_free(param);',
                    'param = nullptr;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI destroy must report close failures before freeing param context')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'closeFailed |= std::ferror(qpfile) || std::fclose(qpfile);',
                    'closeFailed |= std::ferror(zoneFile) || std::fclose(zoneFile);',
                    'closeFailed |= std::ferror(dolbyVisionRpu) || std::fclose(dolbyVisionRpu);',
                    'closeFailed |= std::ferror(scenecutAwareQpConfig) || std::fclose(scenecutAwareQpConfig);',
                    'scenecutAwareQpConfig = nullptr;',
                    'closeFailed |= std::ferror(multiViewConfig) || std::fclose(multiViewConfig);',
                    'multiViewConfig = nullptr;',
                    'output->release();',
                    'output->closeFile(0, 0);',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");',
                    'if (param && api)',
                    '    api->param_free(param);',
                    'param = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI destroy must close output handles before releasing the output wrapper')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool closeFailed = false;',
                    'bool fileCloseFailed = std::ferror(qpfile) != 0;',
                    'if (std::fclose(qpfile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(zoneFile) != 0;',
                    'if (std::fclose(zoneFile))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(dolbyVisionRpu) != 0;',
                    'if (std::fclose(dolbyVisionRpu))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'bool fileCloseFailed = std::ferror(scenecutAwareQpConfig) != 0;',
                    'if (std::fclose(scenecutAwareQpConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'scenecutAwareQpConfig = nullptr;',
                    'bool fileCloseFailed = std::ferror(multiViewConfig) != 0;',
                    'if (std::fclose(multiViewConfig))',
                    '    fileCloseFailed = true;',
                    'closeFailed |= fileCloseFailed;',
                    'multiViewConfig = nullptr;',
                    'closeFailed |= std::ferror(qpfile) || std::fclose(qpfile);',
                    'output->closeFile(0, 0);',
                    'output->release();',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");',
                    'if (param && api)',
                    '    api->param_free(param);',
                    'param = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden CLI destroy short-circuit close regression: closeFailed |= std::ferror(qpfile) || std::fclose(qpfile);')

    print('CLI destroy close-state guard tests passed')


if __name__ == '__main__':
    main()
