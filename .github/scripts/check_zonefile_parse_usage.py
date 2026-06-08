#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
SHARED_TARGET = Path('source/common/param.h')
GLOBAL_FORBIDDEN_SNIPPETS = (
    'param->rc.zones[i].startFrame = atoi(argLine);',
    'param->rc.zones[i].startFrame = std::atoi(argLine);',
    'param->rc.zones[i].startFrame = atoi(args[1]);',
)
ZONEFILE_FORBIDDEN_SNIPPETS = (
    "char* start = std::strchr(argLine, ' ');",
    'tokenize(start, args, argCount);',
    'if (!zonefileCount)\n            return true;',
    'param->rc.zonefileCount = 0;',
    'param->rc.zones = x265_zone_alloc(param->rc.zonefileCount, 1);',
)
ZONEPARAM_FORBIDDEN_SNIPPETS = (
    'param->rc.zones[i].startFrame = startFrame;',
    'if (cliopt.parseZoneParam(argCount, args, param, i))',
    'api->zone_param_parse(globalParam->rc.zones[zonefileCount].zoneParam, long_options[long_options_index].name, optarg);',
)
GLOBAL_REQUIRED_SNIPPETS = (
    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
    'if (bOutputBitDepthError)',
    'if (!prepareCliApiFromOptions(argc, argv, api))',
    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
    'static bool rewindConfigFile(FILE* configFile, const char* context)',
    'clearerr(configFile);',
    'if (std::fseek(configFile, 0, SEEK_SET))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind %s\\n", context);',
    'validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
)
ZONEFILE_REQUIRED_SNIPPETS = (
    'bool CLIOptions::parseZoneFile()',
    'char **args = (char**)alloca(256 * sizeof(char *));',
    'int zonefileCount = 0;',
    'int lineNumber = 0;',
    'lineNumber++;',
    'if (!zonefileCount)',
    'x265_log(nullptr, X265_LOG_ERROR, "Zone file contains no valid entries\\n");',
    'x265_param stagedParam = *param;',
    'stagedParam.rc.zonefileCount = zonefileCount;',
    'stagedParam.rc.zones = x265_zone_alloc(zonefileCount, 1);',
    'if (!rewindConfigFile(zoneFile, "Zone file"))',
    'lineNumber = 0;',
    'char* start = argLine;',
    'while (*start && !std::isspace((unsigned char)*start))',
    'if (!*start)',
    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
    'int32_t startFrame = 0;',
    'if (!parseCliInt32Token(argLine, startFrame))',
    'stagedParam.rc.zones[i].startFrame = startFrame;',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file start frame at line %d\\n", lineNumber);',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing zone file arguments at line %d\\n", lineNumber);',
    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file arguments at line %d\\n", lineNumber);',
    'param->rc.zonefileCount = zonefileCount;',
    'param->rc.zones = stagedParam.rc.zones;',
)
ZONEPARAM_REQUIRED_SNIPPETS = (
    'bool CLIOptions::parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount)',
    'x265_param* zoneParam = globalParam->rc.zones[zonefileCount].zoneParam;',
    'if (!zoneParam)',
    'x265_log(nullptr, X265_LOG_ERROR, "param alloc failed\\n");',
    'void* zoneSvtHevcParam = zoneParam->svtHevcParam;',
    'std::memcpy(zoneParam, globalParam, sizeof(x265_param));',
    'zoneParam->svtHevcParam = zoneSvtHevcParam;',
    'finalizeZoneParamCopy(zoneParam, globalParam);',
    'if (globalParam->svtHevcParam && !zoneParam->svtHevcParam)',
    "if (c == '?')",
    'bError |= api->zone_param_parse(zoneParam, long_options[long_options_index].name, optarg) != 0;',
    'x265_log(nullptr, X265_LOG_ERROR, "extra unused zone file arguments given <%s>\\n", argv[optind]);',
)
SHARED_REQUIRED_SNIPPETS = (
    'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    shared_path = repo_root / SHARED_TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]
    if not shared_path.is_file():
        return [(SHARED_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    shared_text = shared_path.read_text(encoding='utf-8', errors='ignore')
    zone_param_start = text.find('bool CLIOptions::parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount)')
    parse_start = text.find('bool CLIOptions::parse(int argc, char **argv)', zone_param_start if zone_param_start != -1 else 0)
    zone_file_start = text.find('bool CLIOptions::parseZoneFile()', parse_start if parse_start != -1 else 0)
    rpu_start = text.find('int CLIOptions::rpuParser(', zone_file_start if zone_file_start != -1 else 0)
    zone_param_text = text[zone_param_start:parse_start] if -1 not in (zone_param_start, parse_start) else text
    zone_file_text = text[zone_file_start:rpu_start] if -1 not in (zone_file_start, rpu_start) else text
    failures = []
    for snippet in GLOBAL_FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden zonefile parse regression: {snippet}'))
    for snippet in ZONEFILE_FORBIDDEN_SNIPPETS:
        if snippet in zone_file_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden zonefile parse regression: {snippet}'))
    for snippet in ZONEPARAM_FORBIDDEN_SNIPPETS:
        if snippet in zone_param_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden zonefile parse regression: {snippet}'))
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing zonefile parse guardrail: {snippet}'))
    for snippet in ZONEFILE_REQUIRED_SNIPPETS:
        if snippet not in zone_file_text:
            failures.append((TARGET.as_posix(), 0, f'missing zonefile parse guardrail: {snippet}'))
    for snippet in ZONEPARAM_REQUIRED_SNIPPETS:
        if snippet not in zone_param_text:
            failures.append((TARGET.as_posix(), 0, f'missing zonefile parse guardrail: {snippet}'))
    for snippet in SHARED_REQUIRED_SNIPPETS:
        if snippet not in shared_text:
            failures.append((SHARED_TARGET.as_posix(), 0, f'missing zonefile parse guardrail: {snippet}'))
    if text.count('validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing zonefile parse guardrail: validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))'))
    if text.count('if (!rewindConfigFile(zoneFile, "Zone file"))') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing zonefile parse guardrail: if (!rewindConfigFile(zoneFile, "Zone file"))'))

    rewind_helper_pos = text.find('static bool rewindConfigFile(FILE* configFile, const char* context)')
    clearerr_pos = text.find('clearerr(configFile);', rewind_helper_pos if rewind_helper_pos != -1 else 0)
    rewind_seek_pos = text.find('if (std::fseek(configFile, 0, SEEK_SET))', clearerr_pos if clearerr_pos != -1 else 0)
    rewind_log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind %s\\n", context);', rewind_seek_pos if rewind_seek_pos != -1 else 0)
    if -1 in (rewind_helper_pos, clearerr_pos, rewind_seek_pos, rewind_log_pos) or not (
        rewind_helper_pos < clearerr_pos < rewind_seek_pos < rewind_log_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Zone file parsing must clear EOF state and check fseek() before rewinding config files'))

    count_rewind_pos = zone_file_text.find('if (!rewindConfigFile(zoneFile, "Zone file"))')
    empty_check_pos = zone_file_text.find('if (!zonefileCount)', count_rewind_pos if count_rewind_pos != -1 else 0)
    alloc_pos = zone_file_text.find('stagedParam.rc.zones = x265_zone_alloc(zonefileCount, 1);', empty_check_pos if empty_check_pos != -1 else 0)
    parse_rewind_pos = zone_file_text.find('if (!rewindConfigFile(zoneFile, "Zone file"))', alloc_pos if alloc_pos != -1 else 0)
    free_pos = zone_file_text.find('x265_zone_free(&stagedParam);', parse_rewind_pos if parse_rewind_pos != -1 else 0)
    line_reset_pos = zone_file_text.find('lineNumber = 0;', parse_rewind_pos if parse_rewind_pos != -1 else 0)
    if -1 in (count_rewind_pos, empty_check_pos, alloc_pos, parse_rewind_pos, free_pos, line_reset_pos) or not (
        count_rewind_pos < empty_check_pos < alloc_pos < parse_rewind_pos < free_pos < line_reset_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Zone file parsing must verify rewind success before both empty-file checks and second-pass staged parsing'))

    parse_start_pos = zone_file_text.find('if (!parseCliInt32Token(argLine, startFrame))')
    assign_start_pos = zone_file_text.find('stagedParam.rc.zones[i].startFrame = startFrame;', parse_start_pos if parse_start_pos != -1 else 0)
    prepare_pos = zone_file_text.find('if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))')
    zone_parse_pos = zone_file_text.find('if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))', prepare_pos if prepare_pos != -1 else 0)
    if -1 in (parse_start_pos, assign_start_pos) or not (parse_start_pos < assign_start_pos):
        failures.append((TARGET.as_posix(), 0, 'Zone file parsing must validate startFrame before staging it into zone state'))
    if -1 in (prepare_pos, zone_parse_pos) or not (prepare_pos < zone_parse_pos):
        failures.append((TARGET.as_posix(), 0, 'Zone file parsing must prepare subparse arguments before staged zone parameter parsing'))

    memcpy_pos = zone_param_text.find('std::memcpy(zoneParam, globalParam, sizeof(x265_param));')
    finalize_pos = zone_param_text.find('finalizeZoneParamCopy(zoneParam, globalParam);', memcpy_pos if memcpy_pos != -1 else 0)
    svt_guard_pos = zone_param_text.find('if (globalParam->svtHevcParam && !zoneParam->svtHevcParam)', finalize_pos if finalize_pos != -1 else 0)
    if -1 in (memcpy_pos, finalize_pos, svt_guard_pos) or not (memcpy_pos < finalize_pos < svt_guard_pos):
        failures.append((TARGET.as_posix(), 0, 'Zone parameter parsing must finalize copied zone state before validating restored SVT storage'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check zonefile parsing guardrails in x265cli.cpp')
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

    print('Zonefile parse usage validated')


if __name__ == '__main__':
    main()
