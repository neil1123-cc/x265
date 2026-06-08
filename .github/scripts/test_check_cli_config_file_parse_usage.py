#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_config_file_parse_usage.py')


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


PASS_HEADER = '\n'.join((
    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
    'Char* cursor = start;',
    'while (*cursor)',
    'Char* next = cursor;',
    'bool endedOnWhitespace = *cursor && std::isspace((unsigned char)*cursor);',
    'if (endedOnWhitespace)',
    'next++;',
    'while (*next && std::isspace((unsigned char)*next))',
    'start = next;',
    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
)) + '\n'


PASS_CPP = '\n'.join((
    'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)',
    'return walkConfigTokens(start,',
    'if (argCount + 1 >= maxArgs)',
    'args[argCount] = token;',
    'token[tokenLength] = ch;',
    "token[tokenLength] = '\\0';",
    'argCount++;',
    'x265_log(nullptr, X265_LOG_ERROR, "%s has an unterminated quoted argument\\n", context);',
    'x265_log(nullptr, X265_LOG_ERROR, "%s has an empty argument\\n", context);',
    '}) && (args[argCount] = nullptr, true);',
    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
    'args[argCount++] = (char*)"x265";',
    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
    'static bool rewindConfigFile(FILE* configFile, const char* context)',
    'bool CLIOptions::parseZoneFile()',
    'while (std::isspace((unsigned char)*entry)) entry++;',
    "if (!((*entry == '#') || (*entry == '\\0') || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0)))",
    "if (*entry == '#' || *entry == '\\0' || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0))",
    'char* start = argLine;',
    'if (!*start)',
    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
    'bool CLIOptions::parseScenecutAwareQpConfig()',
    "char* start = std::strchr(argLine, '-');",
    'if (!start)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
    'bool CLIOptions::parseMultiViewConfig(char** fn)',
    "char* start = std::strchr(argLine, '-');",
    'if (!start)',
    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
    'args[argCount++] = (char*)"x265";',
    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
    '#ifdef __cplusplus',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP,
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': 'char* token = std::strtok(start, " \\t");\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden CLI config parse regression: char* token = std::strtok(start, " \\t");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP.replace(
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing CLI config parse guardrail: static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': '\n'.join((
                    'template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>',
                    'static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)',
                    'Char* cursor = start;',
                    'while (*cursor)',
                    'Char* next = cursor;',
                    'bool endedOnWhitespace = *cursor && std::isspace((unsigned char)*cursor);',
                    'start = next;',
                    'if (endedOnWhitespace)',
                    'next++;',
                    'while (*next && std::isspace((unsigned char)*next))',
                    'static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)',
                    'return walkConfigTokens(start,',
                    'if (argCount + 1 >= maxArgs)',
                    'args[argCount] = token;',
                    'token[tokenLength] = ch;',
                    "token[tokenLength] = '\\0';",
                    'argCount++;',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s has an unterminated quoted argument\\n", context);',
                    'x265_log(nullptr, X265_LOG_ERROR, "%s has an empty argument\\n", context);',
                    '}) && (args[argCount] = nullptr, true);',
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)',
                    'args[argCount++] = (char*)"x265";',
                    'return tokenizeConfigFileArgs(start, args, maxArgs, argCount, context) &&',
                    '!rejectCliExitRequest(argCount, args, context, lineNumber);',
                    'static bool rewindConfigFile(FILE* configFile, const char* context)',
                    'bool CLIOptions::parseZoneFile()',
                    'while (std::isspace((unsigned char)*entry)) entry++;',
                    "if (!((*entry == '#') || (*entry == '\\0') || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0)))",
                    "if (*entry == '#' || *entry == '\\0' || (std::strcmp(entry, \"\\r\\n\") == 0) || (std::strcmp(entry, \"\\n\") == 0))",
                    'char* start = argLine;',
                    'if (!*start)',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))',
                    'bool CLIOptions::parseScenecutAwareQpConfig()',
                    "char* start = std::strchr(argLine, '-');",
                    'if (!start)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);',
                    'bool CLIOptions::parseMultiViewConfig(char** fn)',
                    "char* start = std::strchr(argLine, '-');",
                    'if (!start)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing multiview config arguments at line %d\\n", lineNumber);',
                    'args[argCount++] = (char*)"x265";',
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))',
                    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid multiview config arguments at line %d\\n", lineNumber);',
                    '#ifdef __cplusplus',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'walkConfigTokens must consume each token, preserve quoted content, and only advance past trailing whitespace after endToken succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP.replace(
                    '}) && (args[argCount] = nullptr, true);\n'
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)\n'
                    'args[argCount++] = (char*)"x265";\n',
                    'args[argCount++] = (char*)"x265";\n'
                    '}) && (args[argCount] = nullptr, true);\n'
                    'static bool prepareConfigSubparseArgs(char* start, char** args, int maxArgs, int& argCount, const char* context, int lineNumber)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Config sub-parse argument preparation must tokenize into bounded argv storage, null-terminate it, then prepend the dummy x265 argv[0] before exit-option rejection')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP.replace(
                    'char* start = argLine;\n'
                    'if (!*start)\n'
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))\n',
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Zone file entry", lineNumber))\n'
                    'char* start = argLine;\n'
                    'if (!*start)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Zone file parsing must skip blank/comment lines, split the start-frame token first, and only then sub-parse the remaining CLI-style arguments')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP.replace(
                    'if (!start)\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);\n'
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);\n',
                    'if (!start)\n'
                    'if (!prepareConfigSubparseArgs(start, args, 256, argCount, "Scenecut-aware QP config", lineNumber))\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "Missing scenecut-aware QP config arguments at line %d\\n", lineNumber);\n'
                    'x265_log(nullptr, X265_LOG_ERROR, "Invalid scenecut-aware QP config arguments at line %d\\n", lineNumber);\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Scenecut-aware QP config parsing must find the first CLI option token before tokenization and preserve the dedicated missing/invalid diagnostics')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.h': PASS_HEADER,
                'source/x265cli.cpp': PASS_CPP.replace(
                    'args[argCount++] = (char*)"x265";\n'
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))\n'
                    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))\n',
                    'args[argCount++] = (char*)"x265";\n'
                    'if (rejectCliExitRequest(argCount, args, "Multiview config", lineNumber))\n'
                    'if (!tokenizeConfigFileArgs(start, args, 256, argCount, "Multiview config"))\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Multiview config parsing must stage argv[0], tokenize the option payload, reject exit requests, and only then emit the invalid-config diagnostic')

    print('CLI config-file parse guard tests passed')


if __name__ == '__main__':
    main()
