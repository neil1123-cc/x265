#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_multiview_parse_close_state.py')

# Coverage probes used by the scan for multiview parse close-state guardrails.
NORMALIZED_PROBES = (
    'multiview parse failure must stop CLI parsing after cleanup',
    'forbidden multiview parse short-circuit close regression: ',
    'missing multiview parse close-state guardrail: ',
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
                'source/x265cli.cpp': '\n'.join((
                    'return false;',
                    'if (!this->parseMultiViewConfig(inputfn))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to parse multiview config file \\n");',
                    '    bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
                    '    if (std::fclose(this->multiViewConfig))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after parse failure\\n");',
                    '    this->multiViewConfig = nullptr;',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': 'if (!this->parseMultiViewConfig(inputfn))\n{\n    this->multiViewConfig = nullptr;\n}\n'})
        expect_fail(run_checker(root), 'missing multiview parse close-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'return false;',
                    'if (!this->parseMultiViewConfig(inputfn))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Unable to parse multiview config file \\n");',
                    '    bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
                    '    if (std::fclose(this->multiViewConfig))',
                    '        closeFailed = true;',
                    '    if (closeFailed)',
                    '        x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after parse failure\\n");',
                    '    this->multiViewConfig = nullptr;',
                    '    if (std::ferror(this->multiViewConfig) || std::fclose(this->multiViewConfig))',
                    '        return true;',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview parse short-circuit close regression')

    print('Multiview parse close-state guard tests passed')


if __name__ == '__main__':
    main()
