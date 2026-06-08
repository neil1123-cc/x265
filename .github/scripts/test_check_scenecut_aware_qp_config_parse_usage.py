#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scenecut_aware_qp_config_parse_usage.py')

# Coverage probes used by the scan for scenecut-aware QP config parsing guardrails.
NORMALIZED_PROBES = (
    'Scenecut-aware QP config must prepare staged subparse arguments before staged parameter parsing',
    'Scenecut-aware QP config must rewind the config file before reading entries',
    'Scenecut-aware QP config must reject missing entries before committing staged parameters',
    'forbidden scenecut-aware QP config parse regression: ',
    'missing scenecut-aware QP config guardrail: ',
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
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'bool CLIOptions::parseScenecutAwareQpConfig()',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'x265_param stagedParam = *param;',
                    'int lineNumber = 0;',
                    'bool foundConfig = false;',
                    'if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))',
                    'while (std::fgets(line, sizeof(line), scenecutAwareQpConfig))',
                    'lineNumber++;',
                    'validateConfigFileLine(scenecutAwareQpConfig, "Scenecut-aware QP config", lineNumber, line, sizeof(line))',
                    'foundConfig = true;',
                    'if (foundConfig)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Scenecut-aware QP config supports only one entry (extra entry at line %d)\\n", lineNumber);',
                    'if (!foundConfig)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Scenecut-aware QP config contains no valid entries\\n");',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                    'if (cliopt.parseScenecutAwareQpParam(argCount, args, &stagedParam))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'return false;',
                    '*param = stagedParam;',
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    "if (c == '?')",
                    'bError |= api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg) != 0;',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", name, optarg);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'outputBitDepth = atoi(optarg);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'if (!foundConfig)\n        {\n            return true;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'std::free(args);\n            break;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'bool CLIOptions::parseScenecutAwareQpConfig()',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'x265_param stagedParam = *param;',
                    'int lineNumber = 0;',
                    'if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))',
                    'while (std::fgets(line, sizeof(line), scenecutAwareQpConfig))',
                    'lineNumber++;',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                    'if (cliopt.parseScenecutAwareQpParam(argCount, args, &stagedParam))',
                    'if (cliopt.api)',
                    '                    cliopt.api->param_free(cliopt.param);',
                    '                std::exit(1);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    '*param = stagedParam;',
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    "if (c == '?')",
                    'bError |= api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg) != 0;',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", name, optarg);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'bool CLIOptions::parseScenecutAwareQpConfig()',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'x265_param stagedParam = *param;',
                    'int lineNumber = 0;',
                    'if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))',
                    'while (std::fgets(line, sizeof(line), scenecutAwareQpConfig))',
                    'lineNumber++;',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                    'if (cliopt.parseScenecutAwareQpParam(argCount, args, &stagedParam))',
                    'if (cliopt.api)',
                    '                    cliopt.api->param_free(cliopt.param);',
                    '                return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    '*param = stagedParam;',
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    "if (c == '?')",
                    'bError |= api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg) != 0;',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", name, optarg);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'bool CLIOptions::parseScenecutAwareQpConfig()',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'x265_param stagedParam = *param;',
                    'int lineNumber = 0;',
                    'bool foundConfig = false;',
                    'std::rewind(scenecutAwareQpConfig);',
                    'if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))',
                    'while (std::fgets(line, sizeof(line), scenecutAwareQpConfig))',
                    'lineNumber++;',
                    'validateConfigFileLine(scenecutAwareQpConfig, "Scenecut-aware QP config", lineNumber, line, sizeof(line))',
                    'foundConfig = true;',
                    'if (foundConfig)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Scenecut-aware QP config supports only one entry (extra entry at line %d)\\n", lineNumber);',
                    'if (!foundConfig)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Scenecut-aware QP config contains no valid entries\\n");',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                    'if (cliopt.parseScenecutAwareQpParam(argCount, args, &stagedParam))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'return false;',
                    '*param = stagedParam;',
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    "if (c == '?')",
                    'bError |= api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg) != 0;',
                    'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", name, optarg);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden scenecut-aware QP config parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'bool CLIOptions::parseScenecutAwareQpConfig()\n',
            },
        )
        expect_fail(run_checker(root), 'missing scenecut-aware QP config guardrail')

    print('Scenecut-aware QP config parse guard tests passed')


if __name__ == '__main__':
    main()
