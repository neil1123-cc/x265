#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
GLOBAL_REQUIRED_SNIPPETS = (
    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
    'if (bOutputBitDepthError)',
    'if (!prepareCliApiFromOptions(argc, argv, api))',
    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
    'static bool rewindConfigFile(FILE* configFile, const char* context)',
    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
    'validateConfigFileLine(scenecutAwareQpConfig, "Scenecut-aware QP config", lineNumber, line, sizeof(line))',
)
CONFIG_REQUIRED_SNIPPETS = (
    'bool CLIOptions::parseScenecutAwareQpConfig()',
    'x265_param stagedParam = *param;',
    'int lineNumber = 0;',
    'bool foundConfig = false;',
    'if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))',
    'lineNumber++;',
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
)
PARAM_REQUIRED_SNIPPETS = (
    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
    "if (c == '?')",
    'bError |= api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg) != 0;',
    'x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", name, optarg);',
)
GLOBAL_FORBIDDEN_SNIPPETS = (
    'outputBitDepth = atoi(optarg);',
    'outputBitDepth = std::atoi(optarg);',
    'outputBitDepth = x265_atoi(optarg, bError);',
    'bError = !!api->scenecut_aware_qp_param_parse(globalParam, long_options[long_options_index].name, optarg);',
)
CONFIG_FORBIDDEN_SNIPPETS = (
    'std::rewind(scenecutAwareQpConfig);',
    'if (!foundConfig)\n        {\n            return true;',
    'if (cliopt.parseScenecutAwareQpParam(argCount, args, param))',
    'if (cliopt.api)\n                    cliopt.api->param_free(cliopt.param);\n                std::exit(1);',
    'if (cliopt.api)\n                    cliopt.api->param_free(cliopt.param);\n                return false;',
    'std::free(args);\n            break;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    config_start = text.find('bool CLIOptions::parseScenecutAwareQpConfig()')
    param_start = text.find('bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)', config_start if config_start != -1 else 0)
    multiview_start = text.find('bool CLIOptions::parseMultiViewConfig', param_start if param_start != -1 else 0)
    config_text = text[config_start:param_start] if -1 not in (config_start, param_start) else text
    param_text = text[param_start:multiview_start if multiview_start != -1 else len(text)] if param_start != -1 else text
    failures = []
    for snippet in GLOBAL_FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden scenecut-aware QP config parse regression: {snippet}'))
    for snippet in CONFIG_FORBIDDEN_SNIPPETS:
        if snippet in config_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden scenecut-aware QP config parse regression: {snippet}'))
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut-aware QP config guardrail: {snippet}'))
    for snippet in CONFIG_REQUIRED_SNIPPETS:
        if snippet not in config_text:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut-aware QP config guardrail: {snippet}'))
    for snippet in PARAM_REQUIRED_SNIPPETS:
        if snippet not in param_text:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut-aware QP config guardrail: {snippet}'))

    prepare_pos = config_text.find('if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))')
    parse_pos = config_text.find('if (cliopt.parseScenecutAwareQpParam(argCount, args, &stagedParam))', prepare_pos if prepare_pos != -1 else 0)
    rewind_pos = config_text.find('if (!rewindConfigFile(scenecutAwareQpConfig, "Scenecut-aware QP config"))')
    while_pos = config_text.find('while (std::fgets(line, sizeof(line), scenecutAwareQpConfig))', rewind_pos if rewind_pos != -1 else 0)
    missing_pos = config_text.find('if (!foundConfig)')
    assign_pos = config_text.find('*param = stagedParam;', missing_pos if missing_pos != -1 else 0)
    if -1 in (prepare_pos, parse_pos) or not (prepare_pos < parse_pos):
        failures.append((TARGET.as_posix(), 0, 'Scenecut-aware QP config must prepare staged subparse arguments before staged parameter parsing'))
    if -1 in (rewind_pos, while_pos) or not (rewind_pos < while_pos):
        failures.append((TARGET.as_posix(), 0, 'Scenecut-aware QP config must rewind the config file before reading entries'))
    if -1 in (missing_pos, assign_pos) or not (missing_pos < assign_pos):
        failures.append((TARGET.as_posix(), 0, 'Scenecut-aware QP config must reject missing entries before committing staged parameters'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scenecut-aware QP config parsing guardrails in x265cli.cpp')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Scenecut-aware QP config parse usage validated')


if __name__ == '__main__':
    main()
