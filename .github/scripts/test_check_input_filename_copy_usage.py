#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_input_filename_copy_usage.py')

# Coverage probes used by the scan for input filename copy guardrails.
NORMALIZED_PROBES = (
    'forbidden input filename copy regression: ',
    'missing input filename copy guardrail: ',
    '--input handling must route optarg through copyCLIString before returning on overflow',
    'Positional input filename parsing must use copyCLIString before advancing to output filename handling',
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
                    'static bool copyCLIString(char* dst, size_t dstSize, const char* src, const char* context)',
                    'if (!dst || !dstSize || !src)',
                    'size_t length = std::strlen(src);',
                    'if (length >= dstSize)',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s exceeds supported length\\n", context);',
                    'std::memcpy(dst, src, length + 1);',
                    'return true;',
                    'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)',
                    'OPT("input")',
                    'if (!copyCLIString(inputfn[0], 1024, optarg, "Input filename"))',
                    'return true;',
                    'OPT("recon")',
                    '#if !ENABLE_MULTIVIEW',
                    'if (optind < argc && !(*inputfn[0]))',
                    'if (!copyCLIString(inputfn[0], 1024, argv[optind++], "Input filename"))',
                    'return true;',
                    'if (optind < argc && !outputfn)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'std::strcpy(inputfn[0], optarg);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden input filename copy regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool copyCLIString(char* dst, size_t dstSize, const char* src, const char* context)',
                    'if (!dst || !dstSize || !src)',
                    'std::memcpy(dst, src, length + 1);',
                    'size_t length = std::strlen(src);',
                    'if (length >= dstSize)',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s exceeds supported length\\n", context);',
                    'return true;',
                    'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)',
                    'OPT("input")',
                    'if (!copyCLIString(inputfn[0], 1024, optarg, "Input filename"))',
                    'return true;',
                    'OPT("recon")',
                    '#if !ENABLE_MULTIVIEW',
                    'if (optind < argc && !(*inputfn[0]))',
                    'if (!copyCLIString(inputfn[0], 1024, argv[optind++], "Input filename"))',
                    'return true;',
                    'if (optind < argc && !outputfn)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'copyCLIString must reject null and oversized input before copying bytes into the CLI filename buffer')

    print('Input filename copy guard tests passed')


if __name__ == '__main__':
    main()
