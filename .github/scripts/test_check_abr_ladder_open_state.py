#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_ladder_open_state.py')

# Coverage probes used by the scan for ABR ladder open-state guardrails.
NORMALIZED_PROBES = (
    'abr ladder ferror path must test the error bit, still call fclose(), then null out and return true',
    'missing abr ladder open-state guardrail: ',
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
                'source/x265.cpp': '\n'.join((
                    'static bool checkAbrLadder(int argc, char **argv, FILE **abrConfig)',
                    '*abrConfig = x265_fopen(optarg, "rb");',
                    'if (!*abrConfig)',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(*abrConfig))',
                    'bool closeFailed = std::ferror(*abrConfig) != 0;',
                    'if (std::fclose(*abrConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file after open failure\\n");',
                    '*abrConfig = nullptr;',
                    'x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\\n", optarg);',
                    'return true;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': '*abrConfig = x265_fopen(optarg, "rb");\nif (!*abrConfig)\n    return true;\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr ladder open-state guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': '\n'.join((
                    'static bool checkAbrLadder(int argc, char **argv, FILE **abrConfig)',
                    '*abrConfig = x265_fopen(optarg, "rb");',
                    'if (!*abrConfig)',
                    '    x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\\n", optarg);',
                    'else if (std::ferror(*abrConfig))',
                    '    return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'abr ladder open failure must log and return true before ferror handling')

    print('ABR ladder open-state guard tests passed')


if __name__ == '__main__':
    main()
