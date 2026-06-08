#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_multiview_config_parse_usage.py')

# Coverage probes used by the scan for multiview config parse guardrails.
NORMALIZED_PROBES = (
    'Multiview config must rewind the config file before reading entries',
    'missing multiview config parse guardrail: ',
    'forbidden multiview config parse regression: ',
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
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'bool CLIOptions::parseMultiViewConfig(char** fn)',
                    'if (!rewindConfigFile(multiViewConfig, "Multiview config"))',
                    'int stagedNumViews = param->numViews;',
                    'int stagedFormat = param->format;',
                    'int stagedNumInput = 0;',
                    'char stagedInputs[MAX_VIEWS][1024] = {{ 0 }};',
                    'while (std::fgets(line, sizeof(line), multiViewConfig))',
                    'validateConfigFileLine(multiViewConfig, "Multiview config", lineNumber, line, sizeof(line))',
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
                    'bool bNumViewsError = !parseCliIntOptarg(optarg, numViews);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config num-views must be between 1 and 2 at line %d\\n", lineNumber);',
                    'stagedNumViews = numViews;',
                    'bool bFormatError = !parseCliIntOptarg(optarg, format);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config format must be 0 (normal), 1 (side-by-side), or 2 (over-under) at line %d\\n", lineNumber);',
                    'stagedFormat = format;',
                    'OPT("input")',
                    'if (!copyCLIString(stagedInputs[stagedNumInput], 1024, optarg, "Multiview input filename"))',
                    'if (stagedNumInput >= MAX_VIEWS)',
                    'x265_log(nullptr, X265_LOG_ERROR, "too many multiview input files at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unsupported multiview config option \'%s\' at line %d\\n", name, lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused multiview config arguments given <%s> at line %d\\n", args[optind], lineNumber);',
                    'if (stagedNumInput != (stagedFormat ? 1 : stagedNumViews))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config input count does not match format %d\\n", stagedFormat);',
                    'param->numViews = stagedNumViews;',
                    'param->format = stagedFormat;',
                    'if (!copyCLIString(fn[view], 1024, stagedInputs[view], "Multiview input filename"))',
                    'return false;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'OPT("num-views") param->numViews = atoi(optarg);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'if (stagedNumViews > 1)\n                    {\n                        if (0);\n                        OPT("input")\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool CLIOptions::parseMultiViewConfig(char** fn)',
                    'int stagedNumViews = param->numViews;',
                    'int stagedFormat = param->format;',
                    'int stagedNumInput = 0;',
                    'char stagedInputs[MAX_VIEWS][1024] = {{ 0 }};',
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
                    'bool bNumViewsError = !parseCliIntOptarg(optarg, numViews);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config num-views must be between 1 and 2 at line %d\\n", lineNumber);',
                    'stagedNumViews = numViews;',
                    'bool bFormatError = !parseCliIntOptarg(optarg, format);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config format must be 0 (normal), 1 (side-by-side), or 2 (over-under) at line %d\\n", lineNumber);',
                    'stagedFormat = format;',
                    'if (!copyCLIString(stagedInputs[stagedNumInput], 1024, optarg, "Multiview input filename"))',
                    'if (stagedNumInput >= MAX_VIEWS)',
                    'x265_log(nullptr, X265_LOG_ERROR, "too many multiview input files at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused multiview config arguments given <%s> at line %d\\n", args[optind], lineNumber);',
                    'if (stagedNumInput != (stagedFormat ? 1 : stagedNumViews))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config input count does not match format %d\\n", stagedFormat);',
                    'param->numViews = stagedNumViews;',
                    'param->format = stagedFormat;',
                    'if (!copyCLIString(fn[view], 1024, stagedInputs[view], "Multiview input filename"))',
                    'if (api)',
                    '                    api->param_free(param);',
                    '                return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool CLIOptions::parseMultiViewConfig(char** fn)',
                    'int stagedNumViews = param->numViews;',
                    'int stagedFormat = param->format;',
                    'int stagedNumInput = 0;',
                    'char stagedInputs[MAX_VIEWS][1024] = {{ 0 }};',
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
                    'bool bNumViewsError = !parseCliIntOptarg(optarg, numViews);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config num-views must be between 1 and 2 at line %d\\n", lineNumber);',
                    'stagedNumViews = numViews;',
                    'bool bFormatError = !parseCliIntOptarg(optarg, format);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config format must be 0 (normal), 1 (side-by-side), or 2 (over-under) at line %d\\n", lineNumber);',
                    'stagedFormat = format;',
                    'if (!copyCLIString(stagedInputs[stagedNumInput], 1024, optarg, "Multiview input filename"))',
                    'if (stagedNumInput >= MAX_VIEWS)',
                    'x265_log(nullptr, X265_LOG_ERROR, "too many multiview input files at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused multiview config arguments given <%s> at line %d\\n", args[optind], lineNumber);',
                    'if (stagedNumInput != (stagedFormat ? 1 : stagedNumViews))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config input count does not match format %d\\n", stagedFormat);',
                    'param->numViews = stagedNumViews;',
                    'param->format = stagedFormat;',
                    'if (!copyCLIString(fn[view], 1024, stagedInputs[view], "Multiview input filename"))',
                    'if (api)',
                    '                    api->param_free(param);',
                    '                std::exit(1);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'bool CLIOptions::parseMultiViewConfig(char** fn)',
                    'std::rewind(multiViewConfig);',
                    'if (!rewindConfigFile(multiViewConfig, "Multiview config"))',
                    'int stagedNumViews = param->numViews;',
                    'int stagedFormat = param->format;',
                    'int stagedNumInput = 0;',
                    'char stagedInputs[MAX_VIEWS][1024] = {{ 0 }};',
                    'while (std::fgets(line, sizeof(line), multiViewConfig))',
                    'validateConfigFileLine(multiViewConfig, "Multiview config", lineNumber, line, sizeof(line))',
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
                    'bool bNumViewsError = !parseCliIntOptarg(optarg, numViews);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config num-views must be between 1 and 2 at line %d\\n", lineNumber);',
                    'stagedNumViews = numViews;',
                    'bool bFormatError = !parseCliIntOptarg(optarg, format);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config format must be 0 (normal), 1 (side-by-side), or 2 (over-under) at line %d\\n", lineNumber);',
                    'stagedFormat = format;',
                    'OPT("input")',
                    'if (!copyCLIString(stagedInputs[stagedNumInput], 1024, optarg, "Multiview input filename"))',
                    'if (stagedNumInput >= MAX_VIEWS)',
                    'x265_log(nullptr, X265_LOG_ERROR, "too many multiview input files at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unsupported multiview config option \'%s\' at line %d\\n", name, lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused multiview config arguments given <%s> at line %d\\n", args[optind], lineNumber);',
                    'if (stagedNumInput != (stagedFormat ? 1 : stagedNumViews))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Multiview config input count does not match format %d\\n", stagedFormat);',
                    'param->numViews = stagedNumViews;',
                    'param->format = stagedFormat;',
                    'if (!copyCLIString(fn[view], 1024, stagedInputs[view], "Multiview input filename"))',
                    'return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'bool CLIOptions::parseMultiViewConfig(char** fn)\n',
            },
        )
        expect_fail(run_checker(root), 'missing multiview config parse guardrail')

    print('Multiview config parse guard tests passed')


if __name__ == '__main__':
    main()
