#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_zonefile_parse_usage.py')

# Coverage probes used by the scan for zonefile parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden zonefile parse regression: ',
    'missing zonefile parse guardrail: ',
    'missing zonefile parse guardrail: validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
    'missing zonefile parse guardrail: if (!rewindConfigFile(zoneFile, "Zone file"))',
    'Zone file parsing must verify rewind success before both empty-file checks and second-pass staged parsing',
    'Zone file parsing must prepare subparse arguments before staged zone parameter parsing',
    'Zone parameter parsing must finalize copied zone state before validating restored SVT storage',
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
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    '{',
                    '    clearerr(configFile);',
                    '    if (std::fseek(configFile, 0, SEEK_SET))',
                    '        x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind %s\\n", context);',
                    '}',
                    'bool CLIOptions::parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount)',
                    '{',
                    '    x265_param* zoneParam = globalParam->rc.zones[zonefileCount].zoneParam;',
                    '    if (!zoneParam)',
                    '        x265_log(nullptr, X265_LOG_ERROR, "param alloc failed\\n");',
                    '    void* zoneSvtHevcParam = zoneParam->svtHevcParam;',
                    '    std::memcpy(zoneParam, globalParam, sizeof(x265_param));',
                    '    zoneParam->svtHevcParam = zoneSvtHevcParam;',
                    '    finalizeZoneParamCopy(zoneParam, globalParam);',
                    '    if (globalParam->svtHevcParam && !zoneParam->svtHevcParam)',
                    '        return true;',
                    "    if (c == '?')",
                    '        return true;',
                    '    bError |= api->zone_param_parse(zoneParam, long_options[long_options_index].name, optarg) != 0;',
                    '    x265_log(nullptr, X265_LOG_ERROR, "extra unused zone file arguments given <%s>\\n", argv[optind]);',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    '    return false;',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    'char **args = (char**)alloca(256 * sizeof(char *));',
                    'int zonefileCount = 0;',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
                    'if (!rewindConfigFile(zoneFile, "Zone file"))',
                    'return false;',
                    'if (!zonefileCount)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Zone file contains no valid entries\\n");',
                    'x265_param stagedParam = *param;',
                    'stagedParam.rc.zonefileCount = zonefileCount;',
                    'stagedParam.rc.zones = x265_zone_alloc(zonefileCount, 1);',
                    'if (!rewindConfigFile(zoneFile, "Zone file"))',
                    '{',
                    'x265_zone_free(&stagedParam);',
                    'return false;',
                    '}',
                    'lineNumber = 0;',
                    'validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
                    'char* start = argLine;',
                    'while (*start && !std::isspace((unsigned char)*start))',
                    'if (!*start)',
                    'int32_t startFrame = 0;',
                    'if (!parseCliInt32Token(argLine, startFrame))',
                    'stagedParam.rc.zones[i].startFrame = startFrame;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file start frame at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing zone file arguments at line %d\\n", lineNumber);',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
                    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file arguments at line %d\\n", lineNumber);',
                    'param->rc.zonefileCount = zonefileCount;',
                    'param->rc.zones = stagedParam.rc.zones;',
                    '}',
                    'int CLIOptions::rpuParser(x265_picture * pic)',
                    '{',
                    '    return 0;',
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
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': 'param->rc.zones[i].startFrame = atoi(argLine);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zonefile parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': "char* start = std::strchr(argLine, ' ');\n",
            },
        )
        expect_fail(run_checker(root), 'forbidden zonefile parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': 'if (!zonefileCount)\n            return true;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden zonefile parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': 'bool CLIOptions::parseZoneFile()\n',
            },
        )
        expect_fail(run_checker(root), 'missing zonefile parse guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    '{',
                    '    clearerr(configFile);',
                    '    if (std::fseek(configFile, 0, SEEK_SET))',
                    '        x265_log(nullptr, X265_LOG_ERROR, "Unable to rewind %s\\n", context);',
                    '}',
                    'bool CLIOptions::parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount)',
                    '{',
                    '    x265_param* zoneParam = globalParam->rc.zones[zonefileCount].zoneParam;',
                    '    void* zoneSvtHevcParam = zoneParam->svtHevcParam;',
                    '    std::memcpy(zoneParam, globalParam, sizeof(x265_param));',
                    '    if (globalParam->svtHevcParam && !zoneParam->svtHevcParam)',
                    '        return true;',
                    '    finalizeZoneParamCopy(zoneParam, globalParam);',
                    "    if (c == '?')",
                    '    bError |= api->zone_param_parse(zoneParam, long_options[long_options_index].name, optarg) != 0;',
                    '    x265_log(nullptr, X265_LOG_ERROR, "extra unused zone file arguments given <%s>\\n", argv[optind]);',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    '    return false;',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    '    if (!rewindConfigFile(zoneFile, "Zone file"))',
                    '        return false;',
                    '    int32_t startFrame = 0;',
                    '    stagedParam.rc.zones[i].startFrame = startFrame;',
                    '    if (!parseCliInt32Token(argLine, startFrame))',
                    '        return false;',
                    '    if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
                    '        return false;',
                    '    if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
                    '        return false;',
                    '}',
                    'int CLIOptions::rpuParser(x265_picture * pic)',
                    '{',
                    '    return 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Zone file parsing must validate startFrame before staging it into zone state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.h': 'void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src);\n',
                'source/x265cli.cpp': '\n'.join((
                    'static bool prepareCliApiFromOptions(int argc, char** argv, const x265_api*& api)',
                    'if (bOutputBitDepthError)',
                    'if (!prepareCliApiFromOptions(argc, argv, api))',
                    'x265_log(nullptr, X265_LOG_ERROR, "invalid argument: %s = %s\\n", "output-depth", optarg);',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    '{',
                    '    clearerr(configFile);',
                    '    std::rewind(zoneFile);',
                    '}',
                    'bool CLIOptions::parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount)',
                    '{',
                    '    x265_param* zoneParam = globalParam->rc.zones[zonefileCount].zoneParam;',
                    '    if (!zoneParam)',
                    '        x265_log(nullptr, X265_LOG_ERROR, "param alloc failed\\n");',
                    '    void* zoneSvtHevcParam = zoneParam->svtHevcParam;',
                    '    std::memcpy(zoneParam, globalParam, sizeof(x265_param));',
                    '    zoneParam->svtHevcParam = zoneSvtHevcParam;',
                    '    finalizeZoneParamCopy(zoneParam, globalParam);',
                    '    if (globalParam->svtHevcParam && !zoneParam->svtHevcParam)',
                    '        return true;',
                    "    if (c == '?')",
                    '        return true;',
                    '    bError |= api->zone_param_parse(zoneParam, long_options[long_options_index].name, optarg) != 0;',
                    '    x265_log(nullptr, X265_LOG_ERROR, "extra unused zone file arguments given <%s>\\n", argv[optind]);',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    '    return false;',
                    '}',
                    'bool CLIOptions::parseZoneFile()',
                    '{',
                    'char **args = (char**)alloca(256 * sizeof(char *));',
                    'int zonefileCount = 0;',
                    'int lineNumber = 0;',
                    'lineNumber++;',
                    'validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
                    'if (!rewindConfigFile(zoneFile, "Zone file"))',
                    'return false;',
                    'if (!zonefileCount)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Zone file contains no valid entries\\n");',
                    'x265_param stagedParam = *param;',
                    'stagedParam.rc.zonefileCount = zonefileCount;',
                    'stagedParam.rc.zones = x265_zone_alloc(zonefileCount, 1);',
                    'if (!rewindConfigFile(zoneFile, "Zone file"))',
                    '{',
                    'x265_zone_free(&stagedParam);',
                    'return false;',
                    '}',
                    'lineNumber = 0;',
                    'validateConfigFileLine(zoneFile, "Zone file", lineNumber, line, sizeof(line))',
                    'char* start = argLine;',
                    'while (*start && !std::isspace((unsigned char)*start))',
                    'if (!*start)',
                    'int32_t startFrame = 0;',
                    'if (!parseCliInt32Token(argLine, startFrame))',
                    'stagedParam.rc.zones[i].startFrame = startFrame;',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file start frame at line %d\\n", lineNumber);',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing zone file arguments at line %d\\n", lineNumber);',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
                    'if (cliopt.parseZoneParam(argCount, args, &stagedParam, i))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid zone file arguments at line %d\\n", lineNumber);',
                    'param->rc.zonefileCount = zonefileCount;',
                    'param->rc.zones = stagedParam.rc.zones;',
                    '}',
                    'int CLIOptions::rpuParser(x265_picture * pic)',
                    '{',
                    '    return 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Zone file parsing must clear EOF state and check fseek() before rewinding config files')

    print('Zonefile parse guard tests passed')


if __name__ == '__main__':
    main()
