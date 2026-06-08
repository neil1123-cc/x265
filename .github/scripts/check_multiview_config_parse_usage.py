#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
GLOBAL_REQUIRED_SNIPPETS = (
    'static bool rewindConfigFile(FILE* configFile, const char* context)',
)
FORBIDDEN_SNIPPETS = (
    'std::rewind(multiViewConfig);',
    'OPT("num-views") param->numViews = atoi(optarg);',
    'OPT("format") param->format = atoi(optarg);',
    'strcpy(fn[numInput], optarg);',
    'if (api)\n                    api->param_free(param);\n                std::exit(1);',
    'if (api)\n                    api->param_free(param);\n                return false;',
    'if (stagedNumViews > 1)\n                    {\n                        if (0);\n                        OPT("input")',
)
REQUIRED_SNIPPETS = (
    'bool CLIOptions::parseMultiViewConfig(char** fn)',
    'if (!rewindConfigFile(multiViewConfig, "Multiview config"))',
    'int stagedNumViews = param->numViews;',
    'int stagedFormat = param->format;',
    'int stagedNumInput = 0;',
    'char stagedInputs[MAX_VIEWS][1024] = {{ 0 }};',
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
)
FORBIDDEN_SNIPPETS += (
    'param->numViews = numViews;',
    'param->format = format;',
    'if (!copyCLIString(fn[numInput], 1024, optarg, "Multiview input filename"))',
    'while (std::fgets(line, sizeof(line), multiViewConfig))\n        {\n            lineNumber++;\n            char* entry = line;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing multiview config parse guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden multiview config parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing multiview config parse guardrail: {snippet}'))
    rewind_pos = text.find('if (!rewindConfigFile(multiViewConfig, "Multiview config"))')
    while_pos = text.find('while (std::fgets(line, sizeof(line), multiViewConfig))', rewind_pos if rewind_pos != -1 else 0)
    if -1 in (rewind_pos, while_pos) or not (rewind_pos < while_pos):
        failures.append((TARGET.as_posix(), 0, 'Multiview config must rewind the config file before reading entries'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check multiview config parsing guardrails in x265cli.cpp')
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

    print('Multiview config parse usage validated')


if __name__ == '__main__':
    main()
